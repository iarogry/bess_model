"""
OPTIMIZER V3-SciPy: Pure Python LP optimization using scipy.optimize.linprog

No external solver binaries needed - uses scipy's built-in Simplex solver.
Fully compatible with V3 interface but with TRUE LP optimization.
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


class Optimizer24hSciPy:
    """24-hour optimizer using scipy.optimize.linprog"""
    
    def __init__(self, config: EnergySourceConfig = None, db_path=DB_PATH):
        self.config = config or EnergySourceConfig()
        self.db_path = db_path
    
    def _load_prices(self, date: str) -> List[float]:
        """Load real hourly prices from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Load all 24 hourly prices for this date
            cursor.execute("""
                SELECT hour, price_hrn_per_mwh FROM prices 
                WHERE date = ? AND hour BETWEEN 1 AND 24
                ORDER BY hour
            """, (date,))
            
            rows = cursor.fetchall()
            
            if len(rows) == 24:
                # We have all 24 hours - use them directly
                prices = [0.0] * 24
                for hour, price in rows:
                    prices[int(hour) - 1] = price
                return prices
            else:
                # Fallback: load daily average and generate synthetic profile
                cursor.execute("""
                    SELECT price_hrn_per_mwh FROM prices 
                    WHERE date = ? AND hour = 24
                """, (date,))
                
                result = cursor.fetchone()
                daily_price = result[0] if result else 2500.0
                
                logger.warning(f"Missing hourly prices for {date}, using synthetic profile from daily avg {daily_price}")
                return self._generate_hourly_prices(daily_price)
        finally:
            conn.close()

    def _generate_hourly_prices(self, daily_price: float) -> List[float]:
        """Generate hourly profile"""
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
        Optimize using scipy.optimize.linprog
        
        Variables (per hour × 24):
          pv_use[h], batt_charge[h], batt_discharge[h], grid_import[h], grid_export[h], soc[h]
        
        Objective: Maximize revenue = Σ(grid_export × price) - Σ(grid_import × price) - losses
        
        Converted to: Minimize -revenue
        """
        
        # Load data
        prices = self._load_prices(date)
        pv_profile = self._get_pv_profile(date)
        demand_profile = self._get_demand_profile(date)
        
        logger.info(f"Optimizing {date} with scipy.optimize.linprog")
        
        # Decision variables (total: 24*6 = 144 variables)
        # For each hour h: [pv_use, batt_charge, batt_discharge, grid_import, grid_export, soc]
        
        n_hours = 24
        n_vars_per_hour = 6
        n_vars = n_hours * n_vars_per_hour
        
        # Index mapping
        def idx(h, var_type):
            # var_type: 0=pv_use, 1=batt_charge, 2=batt_discharge, 3=grid_import, 4=grid_export, 5=soc
            return h * n_vars_per_hour + var_type
        
        # Objective: minimize -revenue (so we maximize revenue)
        c = np.zeros(n_vars)
        tariff_dist = 1.5
        tariff_trans = 0.8
        
        for h in range(n_hours):
            # Maximize grid_export × price (in MWh, so divide by 1000)
            c[idx(h, 4)] -= prices[h] / 1000  # grid_export (kW → MWh conversion)
            
            # Minimize grid_import × (price + tariffs) (in MWh, so divide by 1000)
            c[idx(h, 3)] += (prices[h] + tariff_dist + tariff_trans) / 1000  # grid_import
            
            # Minimize battery losses (in MWh, so divide by 1000)
            loss_percent = 1.0 - self.config.battery_efficiency_round_trip
            c[idx(h, 2)] += loss_percent * (prices[h] + tariff_dist + tariff_trans) / 1000  # batt_discharge
        
        # Bounds for variables
        bounds = []
        for h in range(n_hours):
            bounds.append((0, pv_profile[h]))  # pv_use: 0 to available PV
            bounds.append((0, self.config.battery_max_charge_kw))  # batt_charge
            bounds.append((0, self.config.battery_max_discharge_kw))  # batt_discharge
            bounds.append((0, self.config.grid_max_import_kw))  # grid_import
            bounds.append((0, self.config.grid_max_export_kw))  # grid_export
            bounds.append((
                self.config.battery_capacity_kwh * self.config.battery_soc_min_percent / 100,
                self.config.battery_capacity_kwh * self.config.battery_soc_max_percent / 100
            ))  # soc
        
        # Inequality constraints (A_ub @ x <= b_ub)
        A_ub_list = []
        b_ub_list = []
        
        # Equality constraints (A_eq @ x = b_eq) for SoC dynamics
        A_eq_list = []
        b_eq_list = []
        
        for h in range(n_hours):
            # Energy balance: pv_use + batt_discharge + grid_import >= demand
            # Rewrite as: -pv_use - batt_discharge - grid_import <= -demand
            row = np.zeros(n_vars)
            row[idx(h, 0)] = -1  # pv_use
            row[idx(h, 2)] = -1  # batt_discharge
            row[idx(h, 3)] = -1  # grid_import
            A_ub_list.append(row)
            b_ub_list.append(-demand_profile[h])
            
            # PV balance: pv_use + batt_charge + grid_export <= pv_available
            row = np.zeros(n_vars)
            row[idx(h, 0)] = 1  # pv_use
            row[idx(h, 1)] = 1  # batt_charge
            row[idx(h, 4)] = 1  # grid_export
            A_ub_list.append(row)
            b_ub_list.append(pv_profile[h])
            
            # CRITICAL: Energy conservation - grid_export can only come from available sources
            # grid_export <= pv_used + batt_discharge * efficiency
            # Rewrite as: grid_export - pv_used - batt_discharge*eff <= 0
            row = np.zeros(n_vars)
            row[idx(h, 4)] = 1  # grid_export
            row[idx(h, 0)] = -1  # -pv_used
            row[idx(h, 2)] = -self.config.battery_efficiency_round_trip  # -batt_discharge*0.8
            A_ub_list.append(row)
            b_ub_list.append(0)  # grid_export - pv_used - batt_discharge*0.8 <= 0
            
            # Battery SoC dynamics: soc[h] = soc[h-1] + charge*eff - discharge/eff
            # Rewrite as: -soc[h-1] + soc[h] - charge*eff + discharge/eff = 0
            # For inequality form: 
            # SoC[h] = SoC[h-1] - discharge*1h - discharge*0.2 + charge*1h
            # SoC[h] = SoC[h-1] - 1.2*discharge + charge
            # Rearranged: SoC[h] - SoC[h-1] + 1.2*discharge - charge = 0
            
            row = np.zeros(n_vars)
            row[idx(h, 1)] = -1.0  # -charge (energy in, with 1h conversion)
            row[idx(h, 2)] = 1.2  # discharge (with 20% loss = 1.2x factor)
            row[idx(h, 5)] = 1  # soc[h]
            
            if h == 0:
                A_eq_list.append(row)
                b_eq_list.append(initial_soc_kwh)
            else:
                row[idx(h-1, 5)] = -1  # -soc[h-1]
                A_eq_list.append(row)
                b_eq_list.append(0)
        
        A_ub = np.array(A_ub_list)
        b_ub = np.array(b_ub_list)
        A_eq = np.array(A_eq_list) if A_eq_list else None
        b_eq = np.array(b_eq_list) if b_eq_list else None
        
        # Solve LP
        n_ub = len(b_ub) if A_ub_list else 0
        n_eq = len(b_eq) if A_eq_list else 0
        logger.info(f"Solving LP: {n_vars} variables, {n_ub} inequality + {n_eq} equality constraints")
        
        try:
            result = linprog(
                c, 
                A_ub=A_ub if A_ub_list else None, 
                b_ub=b_ub if A_ub_list else None,
                A_eq=A_eq,
                b_eq=b_eq,
                bounds=bounds,
                method='highs',  # Modern interior-point solver
                options={'disp': False}
            )
            
            if not result.success:
                logger.warning(f"LP solver failed: {result.message}. Using greedy fallback.")
                return self._optimize_day_greedy(date, initial_soc_kwh)
            
            x = result.x
            
        except Exception as e:
            logger.warning(f"LP error: {e}. Using greedy fallback.")
            return self._optimize_day_greedy(date, initial_soc_kwh)
        
        # Extract solution
        dispatch = []
        total_revenue = 0.0
        
        for h in range(n_hours):
            pv_used = x[idx(h, 0)]
            batt_charge = x[idx(h, 1)]
            batt_discharge = x[idx(h, 2)]
            grid_import = x[idx(h, 3)]
            grid_export = x[idx(h, 4)]
            soc = x[idx(h, 5)]
            
            # Revenue calculation (convert kW to MWh by dividing by 1000)
            loss_percent = 1.0 - self.config.battery_efficiency_round_trip
            revenue = (
                grid_export * prices[h] / 1000 -
                grid_import * (prices[h] + 1.5 + 0.8) / 1000 -
                batt_discharge * loss_percent * (prices[h] + 1.5 + 0.8) / 1000
            )
            
            total_revenue += revenue
            
            soc_before = x[idx(h-1, 5)] if h > 0 else initial_soc_kwh
            
            dispatch.append({
                "hour": h,
                "price_rdn": prices[h],
                "demand": demand_profile[h],
                "pv_available": pv_profile[h],
                "pv_used": pv_used,
                "battery_charge": batt_charge,
                "battery_discharge": batt_discharge,
                "grid_import": grid_import,
                "grid_export": grid_export,
                "soc_before": soc_before,
                "soc_after": soc,
                "revenue": revenue,
                "optimizer": "LP-SciPy"
            })
        
        logger.info(f"LP-SciPy optimization complete: {date} → Revenue: {total_revenue:,.0f} грн")
        
        return {
            "date": date,
            "total_revenue": total_revenue,
            "final_soc": x[idx(23, 5)],
            "dispatch": dispatch,
            "optimizer_used": "LP-SciPy"
        }
    
    def _optimize_day_greedy(self, date: str, initial_soc_kwh: float) -> Dict:
        """Greedy fallback (same as V3)"""
        prices = self._load_prices(date)
        pv_profile = self._get_pv_profile(date)
        demand_profile = self._get_demand_profile(date)
        
        logger.info(f"Using greedy fallback for {date}")
        
        dispatch = []
        current_soc = initial_soc_kwh
        total_revenue = 0.0
        
        for h in range(24):
            pv_used = min(pv_profile[h], demand_profile[h])
            demand_remaining = demand_profile[h] - pv_used
            
            batt_discharge = 0.0
            if demand_remaining > 0 and current_soc > 0:
                max_discharge = current_soc / 1.0
                batt_discharge = min(demand_remaining, max_discharge)
                demand_remaining -= batt_discharge
            
            grid_import = max(0, demand_remaining)
            pv_surplus = pv_profile[h] - pv_used
            soc_after_discharge = current_soc - batt_discharge * 1.0
            
            batt_charge = 0.0
            grid_export = 0.0
            
            if pv_surplus > 0:
                max_charge_kwh = self.config.battery_capacity_kwh - soc_after_discharge
                max_charge_kw = max_charge_kwh / 1.0
                
                batt_charge = min(pv_surplus, max_charge_kw)
                stored_kwh = batt_charge * 1.0 * self.config.battery_efficiency_round_trip
                soc_after_discharge += stored_kwh
                grid_export = max(0, pv_surplus - batt_charge)
            
            current_soc = min(self.config.battery_capacity_kwh, max(0, soc_after_discharge))
            
            loss_percent = 1.0 - self.config.battery_efficiency_round_trip
            revenue = (
                grid_export * prices[h] / 1000 -
                grid_import * (prices[h] + 1.5 + 0.8) / 1000 -
                batt_discharge * loss_percent * (prices[h] + 1.5 + 0.8) / 1000
            )
            
            total_revenue += revenue
            
            dispatch.append({
                "hour": h,
                "price_rdn": prices[h],
                "demand": demand_profile[h],
                "pv_available": pv_profile[h],
                "pv_used": pv_used,
                "battery_charge": batt_charge,
                "battery_discharge": batt_discharge,
                "grid_import": grid_import,
                "grid_export": grid_export,
                "soc_before": current_soc - batt_charge * 1.0 * self.config.battery_efficiency_round_trip + batt_discharge * 1.0,
                "soc_after": current_soc,
                "revenue": revenue,
                "optimizer": "GREEDY"
            })
        
        return {
            "date": date,
            "total_revenue": total_revenue,
            "final_soc": current_soc,
            "dispatch": dispatch,
            "optimizer_used": "GREEDY"
        }
