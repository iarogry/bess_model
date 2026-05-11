"""
OPTIMIZER V5-SciPy: Grid Charging + Arbitrage Strategy

Key improvement from V4:
- V4: Battery charges ONLY from PV
- V5: Battery can charge from GRID in low-price hours, discharge in high-price hours

This enables price arbitrage:
  Low price (night): buy cheap grid power → charge battery
  High price (day): discharge battery → sell at premium

Variables per hour (10 per hour, 240 total = 24h × 10 vars):
  pv_to_demand[h], pv_to_export[h], pv_to_charge[h]
  batt_charge[h], batt_discharge[h]
  grid_import[h], grid_export[h], grid_to_batt[h]  ← NEW: grid to battery
  soc[h]

This allows LP to decide: grid_import = grid_to_demand + grid_to_batt
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging
import math
import numpy as np
from scipy.optimize import linprog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data.db"


class EnergySourceConfig:
    """Configuration for all energy sources"""
    
    def __init__(self):
        # PV Solar
        self.pv_capacity_kw = 2500
        self.pv_efficiency = 0.95
        
        # Battery Storage
        self.battery_capacity_kwh = 5000
        self.battery_soc_min_percent = 20
        self.battery_soc_max_percent = 80
        self.battery_efficiency_round_trip = 0.80  # 20% loss
        self.battery_max_charge_kw = 500
        self.battery_max_discharge_kw = 500
        
        # CHP
        self.chp_enabled = True
        self.chp_capacity_kw = 1000
        self.chp_efficiency_elec = 0.40
        self.chp_fuel_cost_hrn_per_mwh = 3500
        self.chp_startup_cost_hrn = 1000
        self.chp_min_load_percent = 30
        
        # Grid
        self.grid_max_import_kw = 5000
        self.grid_max_export_kw = 5000


class Optimizer24hV5SciPy:
    """24-hour optimizer V5 with grid charging for battery arbitrage"""
    
    def __init__(self, config: EnergySourceConfig = None, db_path=DB_PATH):
        self.config = config or EnergySourceConfig()
        self.db_path = db_path
    
    def _load_prices(self, date: str) -> List[float]:
        """Load real hourly prices from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT hour, price_hrn_per_mwh FROM prices 
                WHERE date = ? AND hour BETWEEN 1 AND 24
                ORDER BY hour
            """, (date,))
            
            rows = cursor.fetchall()
            
            if len(rows) == 24:
                prices = [0.0] * 24
                for hour, price in rows:
                    prices[int(hour) - 1] = price
                return prices
            else:
                cursor.execute("""
                    SELECT price_hrn_per_mwh FROM prices 
                    WHERE date = ? AND hour = 24
                """, (date,))
                
                result = cursor.fetchone()
                daily_price = result[0] if result else 2500.0
                
                logger.warning(f"Missing hourly prices for {date}, using synthetic profile")
                return self._generate_hourly_prices(daily_price)
        finally:
            conn.close()

    def _generate_hourly_prices(self, daily_price: float) -> List[float]:
        """Generate hourly price profile"""
        return [
            daily_price * 0.7 if h < 6 else
            daily_price * 1.3 if 10 <= h < 16 else
            daily_price * 0.9 if 16 <= h < 22 else
            daily_price * 0.7
            for h in range(24)
        ]
    
    def _get_pv_profile(self, date: str) -> List[float]:
        """Generate PV profile"""
        day_of_year = datetime.strptime(date, "%Y-%m-%d").timetuple().tm_yday
        seasonal_factor = 0.5 + 0.5 * math.sin((day_of_year - 80) * math.pi / 365)
        
        max_capacity_kw = self.config.pv_capacity_kw
        return [
            max_capacity_kw * seasonal_factor * max(0, math.sin((h - 6) * math.pi / 12))
            if 6 <= h <= 18 else 0
            for h in range(24)
        ]
    
    def _get_demand_profile(self, date: str) -> List[float]:
        """Generate demand profile"""
        daily_demand = 170.0
        
        hourly_factor = [
            0.5 if h < 6 else
            1.2 if 6 <= h < 18 else
            0.8
            for h in range(24)
        ]
        
        sum_factor = sum(hourly_factor)
        avg_per_hour = daily_demand / 24.0
        
        return [factor * avg_per_hour / (sum_factor / 24.0) for factor in hourly_factor]
    
    def optimize_day(self, date: str, initial_soc_kwh: float = 2500.0) -> Dict:
        """
        Optimize using scipy.optimize.linprog with V5 formulation
        
        V5: Battery can charge from GRID (in addition to PV)
        This enables price arbitrage: buy low, sell high
        
        Variables (per hour × 24):
          0: pv_to_demand[h]
          1: pv_to_export[h]
          2: pv_to_charge[h]
          3: batt_charge[h]
          4: batt_discharge[h]
          5: grid_import[h]
          6: grid_export[h]
          7: grid_to_batt[h]  ← NEW: grid power to battery (arbitrage)
          8: soc[h]
        
        Total: 24*9 = 216 variables
        """
        
        # Load data
        prices = self._load_prices(date)
        pv_profile = self._get_pv_profile(date)
        demand_profile = self._get_demand_profile(date)
        
        logger.info(f"[V5] Optimizing {date} with grid charging (arbitrage enabled)")
        
        n_hours = 24
        n_vars_per_hour = 9
        n_vars = n_hours * n_vars_per_hour
        
        # Index mapping
        def idx(h, var_type):
            # var_type: 0=pv_to_demand, 1=pv_to_export, 2=pv_to_charge,
            #           3=batt_charge, 4=batt_discharge, 5=grid_import, 
            #           6=grid_export, 7=grid_to_batt, 8=soc
            return h * n_vars_per_hour + var_type
        
        # Objective: minimize cost, maximize revenue
        c = np.zeros(n_vars)
        tariff_dist = 1.5
        tariff_trans = 0.8
        
        for h in range(n_hours):
            # Maximize grid_export × price
            c[idx(h, 6)] = -prices[h] / 1000  # grid_export
            
            # Minimize grid_import × (price + tariff)
            c[idx(h, 5)] = (prices[h] + tariff_dist + tariff_trans) / 1000  # grid_import
            
            # Battery discharge losses
            loss_factor = 1.0 / self.config.battery_efficiency_round_trip
            c[idx(h, 4)] = loss_factor * (prices[h] + tariff_dist + tariff_trans) / 1000
            
            # Grid to battery: pay full price to charge from grid
            # But we want to buy low, so this is negative cost (benefit if price is low)
            # Actually, we want to minimize: grid_to_batt × price (buy cheap)
            c[idx(h, 7)] = prices[h] / 1000  # grid_to_batt cost
        
        # Bounds
        bounds = []
        for h in range(n_hours):
            bounds.append((0, pv_profile[h]))  # pv_to_demand
            bounds.append((0, pv_profile[h]))  # pv_to_export
            bounds.append((0, pv_profile[h]))  # pv_to_charge
            bounds.append((0, self.config.battery_max_charge_kw))  # batt_charge
            bounds.append((0, self.config.battery_max_discharge_kw))  # batt_discharge
            bounds.append((0, self.config.grid_max_import_kw))  # grid_import
            bounds.append((0, self.config.grid_max_export_kw))  # grid_export
            bounds.append((0, self.config.battery_max_charge_kw))  # grid_to_batt (NEW)
            bounds.append((
                self.config.battery_capacity_kwh * self.config.battery_soc_min_percent / 100,
                self.config.battery_capacity_kwh * self.config.battery_soc_max_percent / 100
            ))  # soc
        
        # Constraints
        A_ub_list = []
        b_ub_list = []
        A_eq_list = []
        b_eq_list = []
        
        for h in range(n_hours):
            # ===== CONSTRAINT 1: PV conservation =====
            row = np.zeros(n_vars)
            row[idx(h, 0)] = 1  # pv_to_demand
            row[idx(h, 1)] = 1  # pv_to_export
            row[idx(h, 2)] = 1  # pv_to_charge
            A_eq_list.append(row)
            b_eq_list.append(pv_profile[h])
            
            # ===== CONSTRAINT 2: Energy balance (demand satisfaction) =====
            # pv_to_demand + batt_discharge + grid_import >= demand
            # (Note: grid_to_batt is part of grid_import, handled separately)
            row = np.zeros(n_vars)
            row[idx(h, 0)] = -1  # pv_to_demand
            row[idx(h, 4)] = -1  # batt_discharge
            row[idx(h, 5)] = -1  # grid_import (includes grid_to_batt)
            A_ub_list.append(row)
            b_ub_list.append(-demand_profile[h])
            
            # ===== CONSTRAINT 3: Battery charging from PV + Grid =====
            # batt_charge = pv_to_charge + grid_to_batt
            # Rewrite as: batt_charge - pv_to_charge - grid_to_batt = 0
            row = np.zeros(n_vars)
            row[idx(h, 3)] = 1  # batt_charge
            row[idx(h, 2)] = -1  # -pv_to_charge
            row[idx(h, 7)] = -1  # -grid_to_batt
            A_eq_list.append(row)
            b_eq_list.append(0)
            
            # ===== CONSTRAINT 4: Grid import accounting =====
            # grid_import = grid_to_demand + grid_to_batt + grid_to_export_loss
            # Simplify: grid_import >= grid_to_batt (covers all uses)
            row = np.zeros(n_vars)
            row[idx(h, 5)] = 1  # grid_import
            row[idx(h, 7)] = -1  # -grid_to_batt
            A_ub_list.append(row)
            b_ub_list.append(0)  # grid_import >= grid_to_batt
            
            # ===== CONSTRAINT 5: Grid export sources =====
            # grid_export <= pv_to_export + batt_discharge*eff
            row = np.zeros(n_vars)
            row[idx(h, 6)] = 1  # grid_export
            row[idx(h, 1)] = -1  # -pv_to_export
            row[idx(h, 4)] = -self.config.battery_efficiency_round_trip  # -batt_discharge*0.8
            A_ub_list.append(row)
            b_ub_list.append(0)
            
            # ===== CONSTRAINT 6: SoC dynamics =====
            charge_eff = math.sqrt(self.config.battery_efficiency_round_trip)
            
            row = np.zeros(n_vars)
            row[idx(h, 3)] = charge_eff  # batt_charge * charge_eff
            row[idx(h, 4)] = -1  # -batt_discharge
            row[idx(h, 8)] = 1  # soc[h]
            
            if h == 0:
                A_eq_list.append(row)
                b_eq_list.append(initial_soc_kwh)
            else:
                row[idx(h-1, 8)] = -1  # -soc[h-1]
                A_eq_list.append(row)
                b_eq_list.append(0)
        
        A_ub = np.array(A_ub_list) if A_ub_list else None
        b_ub = np.array(b_ub_list) if A_ub_list else None
        A_eq = np.array(A_eq_list) if A_eq_list else None
        b_eq = np.array(b_eq_list) if A_eq_list else None
        
        n_ub = len(b_ub) if b_ub is not None else 0
        n_eq = len(b_eq) if b_eq is not None else 0
        logger.info(f"[V5] LP: {n_vars} variables, {n_ub} inequality + {n_eq} equality constraints")
        
        try:
            result = linprog(
                c,
                A_ub=A_ub,
                b_ub=b_ub,
                A_eq=A_eq,
                b_eq=b_eq,
                bounds=bounds,
                method='highs',
                options={'disp': False}
            )
            
            if not result.success:
                logger.warning(f"[V5] LP solver failed: {result.message}. Using fallback.")
                return self._optimize_day_fallback(date, initial_soc_kwh)
            
            x = result.x
            
        except Exception as e:
            logger.warning(f"[V5] LP error: {e}. Using fallback.")
            return self._optimize_day_fallback(date, initial_soc_kwh)
        
        # Extract solution
        dispatch = []
        total_revenue = 0.0
        cumulative_energy_balance = 0.0
        charge_eff = math.sqrt(self.config.battery_efficiency_round_trip)
        
        for h in range(n_hours):
            pv_to_demand = x[idx(h, 0)]
            pv_to_export = x[idx(h, 1)]
            pv_to_charge = x[idx(h, 2)]
            batt_charge = x[idx(h, 3)]
            batt_discharge = x[idx(h, 4)]
            grid_import = x[idx(h, 5)]
            grid_export = x[idx(h, 6)]
            grid_to_batt = x[idx(h, 7)]
            soc = x[idx(h, 8)]
            
            # Validate energy balance
            energy_supplied = pv_to_demand + batt_discharge + (grid_import - grid_to_batt)
            energy_demanded = demand_profile[h]
            balance_error = energy_supplied - energy_demanded
            cumulative_energy_balance += balance_error
            
            # Revenue
            loss_factor = 1.0 / self.config.battery_efficiency_round_trip
            revenue = (
                grid_export * prices[h] / 1000 -
                (grid_import - grid_to_batt) * (prices[h] + 1.5 + 0.8) / 1000 -
                grid_to_batt * prices[h] / 1000 -  # Cost of buying grid for battery
                batt_discharge * (loss_factor - 1.0) * (prices[h] + 1.5 + 0.8) / 1000
            )
            total_revenue += revenue
            
            soc_before = x[idx(h-1, 8)] if h > 0 else initial_soc_kwh
            
            dispatch.append({
                "hour": h,
                "price_rdn": prices[h],
                "demand": demand_profile[h],
                "pv_available": pv_profile[h],
                "pv_to_demand": pv_to_demand,
                "pv_to_export": pv_to_export,
                "pv_to_charge": pv_to_charge,
                "pv_total": pv_to_demand + pv_to_export + pv_to_charge,
                "battery_charge": batt_charge,
                "battery_discharge": batt_discharge,
                "grid_import_total": grid_import,
                "grid_import_for_demand": grid_import - grid_to_batt,
                "grid_to_battery": grid_to_batt,
                "grid_export": grid_export,
                "soc_before": soc_before,
                "soc_after": soc,
                "energy_supplied": energy_supplied,
                "energy_demanded": energy_demanded,
                "balance_error": balance_error,
                "revenue": revenue,
                "optimizer": "LP-V5"
            })
        
        total_pv_available = sum(pv_profile)
        pv_utilization = sum(d["pv_total"] for d in dispatch) / total_pv_available if total_pv_available > 0 else 0
        
        logger.info(f"[V5] {date} → Revenue: {total_revenue:,.0f} грн, "
                   f"Energy balance error: {cumulative_energy_balance:.1f} kWh, "
                   f"PV util: {pv_utilization*100:.1f}%, "
                   f"Grid arbitrage: {sum(d['grid_to_battery'] for d in dispatch)/1000:.2f} MWh")
        
        return {
            "date": date,
            "total_revenue": total_revenue,
            "final_soc": x[idx(23, 8)],
            "dispatch": dispatch,
            "optimizer_used": "LP-V5",
            "energy_balance_error": cumulative_energy_balance,
            "pv_utilization": pv_utilization,
            "grid_arbitrage_mwh": sum(d['grid_to_battery'] for d in dispatch) / 1000
        }
    
    def _optimize_day_fallback(self, date: str, initial_soc_kwh: float) -> Dict:
        """Fallback greedy optimizer"""
        prices = self._load_prices(date)
        pv_profile = self._get_pv_profile(date)
        demand_profile = self._get_demand_profile(date)
        
        logger.info(f"[V5] Using greedy fallback for {date}")
        
        dispatch = []
        current_soc = initial_soc_kwh
        total_revenue = 0.0
        cumulative_energy_balance = 0.0
        total_grid_arb = 0.0
        
        for h in range(24):
            pv_to_demand = min(pv_profile[h], demand_profile[h])
            demand_remaining = demand_profile[h] - pv_to_demand
            pv_remaining = pv_profile[h] - pv_to_demand
            
            batt_discharge = 0.0
            if demand_remaining > 0 and current_soc > 0:
                max_discharge = current_soc
                batt_discharge = min(demand_remaining, max_discharge)
                demand_remaining -= batt_discharge
            
            # Grid: either import for demand or for battery charging
            grid_import_for_demand = max(0, demand_remaining)
            
            # Greedy grid arbitrage: if price is low, buy for battery
            grid_to_batt = 0.0
            if prices[h] < 2000:  # Low price threshold
                max_charge = (self.config.battery_capacity_kwh * 
                             self.config.battery_soc_max_percent / 100 - current_soc)
                grid_to_batt = min(100, max_charge)  # Limited arbitrage for safety
                total_grid_arb += grid_to_batt
            
            grid_import = grid_import_for_demand + grid_to_batt
            
            pv_to_charge = 0.0
            pv_to_export = 0.0
            batt_charge = 0.0
            charge_eff = math.sqrt(self.config.battery_efficiency_round_trip)
            
            if pv_remaining > 0:
                if prices[h] > 3000:
                    pv_to_export = pv_remaining
                else:
                    max_charge_kwh = (self.config.battery_capacity_kwh * 
                                     self.config.battery_soc_max_percent / 100 - current_soc - grid_to_batt)
                    pv_to_charge = min(pv_remaining, max(0, max_charge_kwh))
                    batt_charge = pv_to_charge + grid_to_batt
                    pv_to_export = pv_remaining - pv_to_charge
            
            # Update SoC
            soc_change = batt_charge * charge_eff - batt_discharge
            current_soc = max(
                self.config.battery_capacity_kwh * self.config.battery_soc_min_percent / 100,
                min(
                    self.config.battery_capacity_kwh * self.config.battery_soc_max_percent / 100,
                    current_soc + soc_change
                )
            )
            
            grid_export = pv_to_export + batt_discharge * self.config.battery_efficiency_round_trip
            
            energy_supplied = pv_to_demand + batt_discharge + grid_import_for_demand
            balance_error = energy_supplied - demand_profile[h]
            cumulative_energy_balance += balance_error
            
            loss_factor = 1.0 / self.config.battery_efficiency_round_trip
            revenue = (
                grid_export * prices[h] / 1000 -
                grid_import_for_demand * (prices[h] + 1.5 + 0.8) / 1000 -
                grid_to_batt * prices[h] / 1000 -
                batt_discharge * (loss_factor - 1.0) * (prices[h] + 1.5 + 0.8) / 1000
            )
            total_revenue += revenue
            
            soc_before = current_soc - soc_change
            
            dispatch.append({
                "hour": h,
                "price_rdn": prices[h],
                "demand": demand_profile[h],
                "pv_available": pv_profile[h],
                "pv_to_demand": pv_to_demand,
                "pv_to_export": pv_to_export,
                "pv_to_charge": pv_to_charge,
                "pv_total": pv_to_demand + pv_to_export + pv_to_charge,
                "battery_charge": batt_charge,
                "battery_discharge": batt_discharge,
                "grid_import_total": grid_import,
                "grid_import_for_demand": grid_import_for_demand,
                "grid_to_battery": grid_to_batt,
                "grid_export": grid_export,
                "soc_before": soc_before,
                "soc_after": current_soc,
                "energy_supplied": energy_supplied,
                "energy_demanded": demand_profile[h],
                "balance_error": balance_error,
                "revenue": revenue,
                "optimizer": "GREEDY-V5"
            })
        
        return {
            "date": date,
            "total_revenue": total_revenue,
            "final_soc": current_soc,
            "dispatch": dispatch,
            "optimizer_used": "GREEDY-V5",
            "energy_balance_error": cumulative_energy_balance,
            "pv_utilization": sum(d["pv_total"] for d in dispatch) / sum(pv_profile) if sum(pv_profile) > 0 else 0,
            "grid_arbitrage_mwh": total_grid_arb / 1000
        }
