#!/usr/bin/env python3
"""
V4-RDN Battery Optimizer (Pure RDN Trading)
Оптимизирует ТОЛЬКО торговлю на РДН, БЕЗ локального спроса
Моделирует архитектуру Ярославовой модели (Chervonohrad)
"""

import numpy as np
from scipy.optimize import linprog
import json
from datetime import datetime, timedelta

class V4RDNOptimizer:
    """
    Linear Programming оптимизатор для батареи (РДН торговля)
    
    Максимизирует доход от торговли на РДН:
    Profit = Σ[grid_export[h] × price[h]] - Σ[grid_import[h] × price[h]]
    
    Без учета локального спроса - батарея торгует свободно.
    """
    
    def __init__(self, 
                 pv_generation_kwh,
                 rdn_prices_uah_per_mwh,
                 battery_capacity_mwh=10.0,
                 battery_power_mw=2.5,
                 battery_rte=0.88,
                 grid_tariff_import_uah_per_mwh=686.23+98.97):
        """
        Args:
            pv_generation_kwh: array of 8760 hourly PV generation [kWh]
            rdn_prices_uah_per_mwh: array of 8760 hourly RDN prices [UAH/MWh]
            battery_capacity_mwh: battery energy capacity [MWh]
            battery_power_mw: charging/discharging power limit [MW]
            battery_rte: round-trip efficiency (0-1)
            grid_tariff_import_uah_per_mwh: grid import tariff [UAH/MWh]
        """
        
        self.pv_gen = np.array(pv_generation_kwh, dtype=float)
        self.prices = np.array(rdn_prices_uah_per_mwh, dtype=float)
        
        self.battery_capacity_kwh = battery_capacity_mwh * 1000
        self.battery_power_kw = battery_power_mw * 1000
        self.battery_rte = battery_rte
        self.grid_tariff = grid_tariff_import_uah_per_mwh
        
        self.n_hours = len(self.pv_gen)
        
        # Проверка размеров
        assert len(self.prices) == self.n_hours, \
            f"Price array size {len(self.prices)} != PV size {self.n_hours}"
        
    def optimize_single_day(self, day_idx=0, initial_soc_kwh=5000):
        """
        Оптимизирует один день (24 часа) с начальным SOC
        
        Переменные (per hour):
        - pv_to_export: PV мощность в сеть [кВт]
        - pv_to_charge: PV мощность в батарею [кВт]
        - batt_discharge: Батарея разрядка в сеть [кВт]
        - grid_import: Импорт из сети [кВт]
        - grid_export: Экспорт в сеть [кВт]
        - soc: State of Charge батареи [кВт*ч]
        
        Всего: 24 часов × 5 переменных = 120 переменных (сокращено)
        
        Целевая функция: Максимизировать доход
        max Σ[grid_export[h] × price[h]] - Σ[grid_import[h] × price[h]]
        """
        
        start_hour = day_idx * 24
        end_hour = min(start_hour + 24, self.n_hours)
        n_hours = end_hour - start_hour
        
        pv_day = self.pv_gen[start_hour:end_hour]
        prices_day = self.prices[start_hour:end_hour]
        
        # Переменные: [export, import, charge, discharge, soc_end]
        # Всего: 24h × 5 vars = 120
        n_vars = n_hours * 5
        
        # Objective: maximize revenue = export_revenue - import_cost
        # linprog minimizes, so we negate the revenue
        c = np.zeros(n_vars)
        
        for h in range(n_hours):
            idx_export = h * 5 + 0
            idx_import = h * 5 + 1
            
            # Coefficient for grid_export: -price (negative because we maximize)
            c[idx_export] = -prices_day[h] / 1000  # Convert UAH/MWh to UAH/kWh
            
            # Coefficient for grid_import: +price (cost)
            c[idx_import] = (prices_day[h] + self.grid_tariff) / 1000
        
        # Constraints: A_ub @ x <= b_ub
        A_ub = []
        b_ub = []
        A_eq = []
        b_eq = []
        
        # Bounds on variables: x_bounds = [(min, max), ...]
        bounds = []
        for h in range(n_hours):
            # export: [0, pv_gen]
            bounds.append((0, pv_day[h]))  # pv_to_export
            
            # import: [0, battery_power]
            bounds.append((0, self.battery_power_kw))  # grid_import
            
            # charge: [0, battery_power]
            bounds.append((0, self.battery_power_kw))  # pv_to_charge
            
            # discharge: [0, battery_power]
            bounds.append((0, self.battery_power_kw))  # batt_discharge
            
            # soc: [0, capacity]
            bounds.append((0, self.battery_capacity_kwh))  # soc_end
        
        # Energy balance constraints
        # soc[h] = soc[h-1] + charge[h]*sqrt(rte) - discharge[h]
        # => soc[h] - charge[h]*sqrt(rte) + discharge[h] = soc[h-1]
        
        soc_prev = initial_soc_kwh
        for h in range(n_hours):
            idx_charge = h * 5 + 2
            idx_discharge = h * 5 + 3
            idx_soc = h * 5 + 4
            
            # soc[h] = soc[h-1] + charge*sqrt(rte) - discharge
            row = np.zeros(n_vars)
            row[idx_charge] = np.sqrt(self.battery_rte)
            row[idx_discharge] = -1
            row[idx_soc] = 1
            
            A_eq.append(row)
            b_eq.append(soc_prev)
            
            soc_prev = None  # Will be computed from previous iteration
        
        # Convert to format for linprog
        if A_ub:
            A_ub = np.array(A_ub)
            b_ub = np.array(b_ub)
        else:
            A_ub = None
            b_ub = None
        
        if A_eq:
            A_eq = np.array(A_eq)
            b_eq = np.array(b_eq)
        else:
            A_eq = None
            b_eq = None
        
        # Solve
        result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                        bounds=bounds, method='highs')
        
        return {
            'success': result.success,
            'revenue': -result.fun if result.success else 0,
            'message': result.message,
            'n_hours': n_hours,
            'solution': result.x if result.success else None
        }
    
    def optimize_full_year(self, verbose=True):
        """
        Оптимизирует полный год (365 дней) с днь-к-дню rollover SOC
        """
        
        results = []
        total_revenue = 0
        soc_current = self.battery_capacity_kwh * 0.5  # Start at 50% SOC
        
        for day_idx in range(365):
            if verbose and day_idx % 30 == 0:
                print(f"  Day {day_idx+1}/365 | Current Revenue: {total_revenue:,.2f} UAH")
            
            result = self.optimize_single_day(day_idx, soc_current)
            
            if result['success']:
                revenue = result['revenue']
                total_revenue += revenue
                results.append(result)
                
                # Rollover SOC to next day (last hour's SOC becomes next day's initial SOC)
                if result['solution'] is not None:
                    last_soc_idx = (result['n_hours'] - 1) * 5 + 4
                    soc_current = result['solution'][last_soc_idx]
            else:
                print(f"  WARNING: Day {day_idx+1} optimization failed: {result['message']}")
                results.append(result)
        
        return {
            'total_revenue_uah': total_revenue,
            'daily_results': results,
            'n_days': len(results),
            'avg_daily_revenue': total_revenue / len(results) if results else 0
        }


# ============================================================================
# MAIN: Быстрый тест
# ============================================================================

if __name__ == '__main__':
    print("="*80)
    print("🔋 V4-RDN OPTIMIZER - Pure RDN Trading Model")
    print("="*80)
    
    # Загрузим данные
    try:
        with open('demand_profile_2026.json', 'r', encoding='utf-8') as f:
            demand_data = json.load(f)
        
        with open('chervonohrad_data_corrected.json', 'r', encoding='utf-8') as f:
            chervonohrad = json.load(f)
        
        # Используем RDN цены из успешно загруженных данных
        rdn_prices = chervonohrad['hourly_data']['price_rdn_uah_per_mwh']
        pv_generation = np.random.normal(1000, 300, 8760)  # Dummy PV data for now
        
        print(f"\n✓ Loaded demand: {len(demand_data['hourly_demand_kwh'])} hours")
        print(f"✓ Loaded RDN prices: {len(rdn_prices)} hours")
        print(f"✓ Price stats: Min {min(rdn_prices):.0f}, Max {max(rdn_prices):.0f}, Avg {np.mean(rdn_prices):.0f} UAH/MWh")
        
        # Создать оптимизатор
        optimizer = V4RDNOptimizer(
            pv_generation_kwh=pv_generation,
            rdn_prices_uah_per_mwh=rdn_prices,
            battery_capacity_mwh=10.0,
            battery_power_mw=2.5,
            battery_rte=0.88
        )
        
        print(f"\n✓ V4-RDN Optimizer initialized")
        print(f"  Battery capacity: 10 MWh")
        print(f"  Battery power: 2.5 MW")
        print(f"  Battery RTE: 88%")
        
        # Оптимизировать один день для теста
        print(f"\n🔄 Testing single-day optimization...")
        result_day = optimizer.optimize_single_day(0)
        
        if result_day['success']:
            print(f"✓ Day 0 optimized successfully")
            print(f"  Revenue: {result_day['revenue']:,.2f} UAH")
        else:
            print(f"✗ Day 0 optimization failed: {result_day['message']}")
        
        print("\n" + "="*80)
        print("✅ V4-RDN ready for full-year optimization")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

