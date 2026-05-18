"""
OPTIMIZER V5-SciPy: Grid Charging + Arbitrage Strategy
(UPDATED: Method 1 - Smart Tariff Allocation for Arbitrage)

Key improvement from V4:
- V4: Battery charges ONLY from PV
- V5: Battery can charge from GRID in low-price hours, discharge in high-price hours

Tariff update in this version:
Distribution and transmission tariffs are applied ONLY to grid energy consumed 
for demand OR lost due to battery round-trip efficiency. Transit energy used 
for arbitrage is NOT heavily penalized, enabling proper market trading.

Variables per hour (10 per hour, 240 total = 24h × 10 vars):
  pv_to_demand[h], pv_to_export[h], pv_to_charge[h]
  batt_charge[h], batt_discharge[h]
  grid_import[h], grid_export[h], grid_to_batt[h]  ← NEW: grid to battery
  soc[h]
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging
import math
import numpy as np
from scipy.optimize import linprog
from dotenv import load_dotenv

# Use centralized PostgreSQL connector
from db_connector import DBConnector

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnergySourceConfig:
    """Configuration for all energy sources"""
    
    def __init__(self):
        # Default Values (will be overridden by _load_from_db)
        self.pv_capacity_kw = 2500
        self.pv_efficiency = 0.95
        self.battery_capacity_kwh = 5000
        self.battery_soc_min_percent = 13
        self.battery_soc_max_percent = 97
        self.battery_efficiency_round_trip = 0.80
        self.battery_max_charge_kw = 2500
        self.battery_max_discharge_kw = 2500
        self.battery_degradation_cost_per_kwh = 0.1125
        self.tariff_distribution = 1500.0
        self.tariff_transmission = 800.0
        self.chp_capacity_kw = 1000
        self.grid_max_import_kw = 5000
        self.grid_max_export_kw = 5000

    def _load_from_db(self):
        """Load configuration from PostgreSQL with unit conversion (MW -> kW)"""
        conn = DBConnector.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT parameter, value FROM system_config")
            rows = cursor.fetchall()
            
            config_dict = {row[0]: row[1] for row in rows}
            
            if config_dict:
                # Helper for unit conversion
                def get_kw(key_mw, key_kw, default_val):
                    if key_mw in config_dict:
                        return float(config_dict[key_mw]) * 1000
                    return float(config_dict.get(key_kw, default_val))

                self.pv_capacity_kw = get_kw("rated_power_mw", "pv_capacity_kw", self.pv_capacity_kw)
                self.battery_capacity_kwh = get_kw("capacity_mwh", "battery_capacity_kwh", self.battery_capacity_kwh)
                self.battery_max_charge_kw = get_kw("max_charge_mw", "battery_max_charge_kw", self.battery_max_charge_kw)
                self.battery_max_discharge_kw = get_kw("max_discharge_mw", "battery_max_discharge_kw", self.battery_max_discharge_kw)
                
                self.battery_soc_min_percent = float(config_dict.get("battery_soc_min_percent", self.battery_soc_min_percent))
                self.battery_soc_max_percent = float(config_dict.get("battery_soc_max_percent", self.battery_soc_max_percent))
                self.battery_efficiency_round_trip = float(config_dict.get("battery_efficiency_round_trip", self.battery_efficiency_round_trip))
                self.battery_degradation_cost_per_kwh = float(config_dict.get("battery_degradation_cost_per_kwh", self.battery_degradation_cost_per_kwh))
                self.tariff_distribution = float(config_dict.get("tariff_distribution", self.tariff_distribution))
                self.tariff_transmission = float(config_dict.get("tariff_transmission", self.tariff_transmission))
                
                logger.info(f"Successfully loaded {len(config_dict)} parameters (with MW -> kW conversion where applicable)")
            
            cursor.close()
        except Exception as e:
            logger.warning(f"Could not load config from Postgres: {e}. Using defaults.")
        finally:
            DBConnector.release_connection(conn)


class Optimizer24hV5SciPy:
    """24-hour optimizer V5 with grid charging for battery arbitrage"""
    
    def __init__(self, config: EnergySourceConfig = None):
        self.config = config or EnergySourceConfig()
    
    def _load_prices(self, date: str) -> List[float]:
        """Load real hourly prices from PostgreSQL"""
        conn = DBConnector.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT hour, price_hrn_per_mwh FROM prices 
                WHERE date = %s AND hour BETWEEN 1 AND 24
                ORDER BY hour
            """, (date,))
            
            rows = cursor.fetchall()
            
            if len(rows) == 24:
                prices = [0.0] * 24
                for hour, price in rows:
                    prices[int(hour) - 1] = float(price)
                return prices
            else:
                logger.warning(f"Missing hourly prices for {date}, using synthetic profile")
                # Fallback to some base price or handle error
                return self._generate_hourly_prices(2500.0)
        finally:
            DBConnector.release_connection(conn)

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
        """Fetch real 24h PV profile from PostgreSQL"""
        conn = DBConnector.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT hour, pv_kw FROM pv_profile 
                WHERE date = %s AND hour BETWEEN 1 AND 24
                ORDER BY hour
            """, (date,))
            
            rows = cursor.fetchall()
            profile = [0.0] * 24
            
            for hour, val in rows:
                profile[int(hour) - 1] = float(val) if val is not None else 0.0
                
            return profile
        except Exception as e:
            logger.warning(f"Error fetching PV profile for {date}: {e}. Using zero profile.")
            return [0.0] * 24
        finally:
            DBConnector.release_connection(conn)
    
    def _get_demand_profile(self, date: str) -> List[float]:
        """Fetch real 24h demand profile from PostgreSQL"""
        conn = DBConnector.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT hour, demand_kw FROM demand 
                WHERE date = %s AND hour BETWEEN 1 AND 24
                ORDER BY hour
            """, (date,))
            
            rows = cursor.fetchall()
            profile = [0.0] * 24
            
            for hour, val in rows:
                profile[int(hour) - 1] = float(val) if val is not None else 0.0
                
            return profile
        except Exception as e:
            logger.warning(f"Error fetching demand profile for {date}: {e}. Using zero profile.")
            return [0.0] * 24
        finally:
            DBConnector.release_connection(conn)
    
    def optimize_day(self, date: str, initial_soc_kwh: float = 2500.0) -> Dict:
        """
        Optimize using scipy.optimize.linprog with V5 formulation
        """
        # Load data
        prices = self._load_prices(date)
        pv_profile = self._get_pv_profile(date)
        demand_profile = self._get_demand_profile(date)
        
        logger.info(f"[V5] Optimizing {date} with grid charging (smart tariff arbitrage enabled)")
        
        n_hours = 24
        n_vars_per_hour = 9
        n_vars = n_hours * n_vars_per_hour
        
        # Index mapping
        def idx(h, var_type):
            return h * n_vars_per_hour + var_type
        
        # Objective: minimize cost, maximize revenue
        c = np.zeros(n_vars)
        tariff_dist = self.config.tariff_distribution / 1000
        tariff_trans = self.config.tariff_transmission / 1000
        tariffs_total = tariff_dist + tariff_trans
        efficiency = self.config.battery_efficiency_round_trip
        
        for h in range(n_hours):
            price_kwh = prices[h] / 1000
            # 1. Export revenue
            c[idx(h, 6)] = -price_kwh
            # 2. Import cost (base)
            c[idx(h, 5)] = price_kwh
            # 3. Tariff logic
            c[idx(h, 5)] += tariffs_total
            c[idx(h, 7)] -= (tariffs_total * efficiency)
            # 4. PV to demand saving
            c[idx(h, 0)] = -(price_kwh + tariffs_total)
            # Micro-penalty for discharge
            c[idx(h, 4)] += 0.0001
        
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
            bounds.append((0, self.config.battery_max_charge_kw))  # grid_to_batt
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
            # PV conservation
            row = np.zeros(n_vars)
            row[idx(h, 0)] = 1; row[idx(h, 1)] = 1; row[idx(h, 2)] = 1
            A_eq_list.append(row); b_eq_list.append(pv_profile[h])
            
            # ===== CONSTRAINT 2: Energy balance (demand satisfaction) =====
            row = np.zeros(n_vars)
            row[idx(h, 0)] = -1  # -pv_to_demand
            row[idx(h, 4)] = -1  # -batt_discharge
            row[idx(h, 5)] = -1  # -grid_import
            row[idx(h, 7)] = 1   # +grid_to_batt (subtracting transit from import)
            A_ub_list.append(row)
            b_ub_list.append(-demand_profile[h])
            
            # ===== CONSTRAINT 3: Battery charging from PV + Grid =====
            row = np.zeros(n_vars)
            row[idx(h, 3)] = 1; row[idx(h, 2)] = -1; row[idx(h, 7)] = -1
            A_eq_list.append(row); b_eq_list.append(0)
            
            # ===== CONSTRAINT 4: Grid import accounting =====
            row = np.zeros(n_vars)
            row[idx(h, 5)] = 1; row[idx(h, 7)] = -1
            A_ub_list.append(row); b_ub_list.append(0)
            
            # ===== CONSTRAINT 5: Grid export sources =====
            row = np.zeros(n_vars)
            row[idx(h, 6)] = 1; row[idx(h, 1)] = -1; row[idx(h, 4)] = -self.config.battery_efficiency_round_trip
            A_ub_list.append(row); b_ub_list.append(0)
            
            # ===== CONSTRAINT 6: SoC dynamics =====
            charge_eff = math.sqrt(self.config.battery_efficiency_round_trip)
            row = np.zeros(n_vars)
            row[idx(h, 3)] = charge_eff; row[idx(h, 4)] = -1; row[idx(h, 8)] = 1
            if h == 0:
                A_eq_list.append(row); b_eq_list.append(initial_soc_kwh)
            else:
                row[idx(h-1, 8)] = -1
                A_eq_list.append(row); b_eq_list.append(0)

            # ===== CONSTRAINT 7: Global AC Bus Balance (Prevents Double Counting) =====
            row = np.zeros(n_vars)
            row[idx(h, 0)] = -1  # -pv_to_demand
            row[idx(h, 1)] = -1  # -pv_to_export
            row[idx(h, 4)] = -1  # -batt_discharge
            row[idx(h, 5)] = -1  # -grid_import
            row[idx(h, 6)] = 1   # +grid_export
            row[idx(h, 7)] = 1   # +grid_to_batt
            A_ub_list.append(row)
            b_ub_list.append(-demand_profile[h])
        
        A_ub = np.array(A_ub_list); b_ub = np.array(b_ub_list)
        A_eq = np.array(A_eq_list); b_eq = np.array(b_eq_list)
        
        try:
            result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
            if not result.success:
                return self._optimize_day_fallback(date, initial_soc_kwh)
            x = result.x
        except Exception:
            return self._optimize_day_fallback(date, initial_soc_kwh)
        
        dispatch = []
        total_revenue = 0.0
        for h in range(n_hours):
            pv_to_demand = x[idx(h, 0)]; grid_import = x[idx(h, 5)]
            grid_export = x[idx(h, 6)]; grid_to_batt = x[idx(h, 7)]; soc = x[idx(h, 8)]
            
            rev_export = grid_export * prices[h] / 1000
            cost_import_base = grid_import * prices[h] / 1000
            taxable_volume = grid_import - (grid_to_batt * efficiency)
            cost_tariffs = taxable_volume * tariffs_total
            
            revenue = rev_export - cost_import_base - cost_tariffs
            total_revenue += revenue
            
            dispatch.append({
                "hour": h, "price_rdn": prices[h], "demand": demand_profile[h],
                "pv_total": x[idx(h, 0)] + x[idx(h, 1)] + x[idx(h, 2)],
                "battery_charge": x[idx(h, 3)], "battery_discharge": x[idx(h, 4)],
                "grid_import_total": grid_import, "grid_export": grid_export,
                "soc_after": soc, "revenue": revenue
            })
            
        return {"date": date, "total_revenue": total_revenue, "final_soc": x[idx(23, 8)], "dispatch": dispatch}

    def _optimize_day_fallback(self, date: str, initial_soc_kwh: float) -> Dict:
        """Simplified greedy fallback logic using PostgreSQL data"""
        prices = self._load_prices(date)
        pv_profile = self._get_pv_profile(date)
        demand_profile = self._get_demand_profile(date)
        
        tariff_total = (self.config.tariff_distribution + self.config.tariff_transmission) / 1000
        efficiency = self.config.battery_efficiency_round_trip
        
        dispatch = []
        current_soc = initial_soc_kwh
        total_revenue = 0.0
        
        for h in range(24):
            # Very basic greedy logic (can be expanded)
            grid_export = 0.0; grid_import = demand_profile[h]; grid_to_batt = 0.0
            
            rev_export = grid_export * prices[h] / 1000
            cost_import_base = grid_import * prices[h] / 1000
            taxable_volume = max(0, grid_import - (grid_to_batt * efficiency))
            cost_tariffs = taxable_volume * tariff_total
            
            hour_revenue = rev_export - cost_import_base - cost_tariffs
            total_revenue += hour_revenue
            
            dispatch.append({
                "hour": h, "price_rdn": prices[h], "demand": demand_profile[h],
                "pv_total": pv_profile[h], "battery_charge": 0.0, "battery_discharge": 0.0,
                "grid_import_total": grid_import, "grid_export": grid_export,
                "soc_after": current_soc, "revenue": hour_revenue
            })
            
        return {"date": date, "total_revenue": total_revenue, "final_soc": current_soc, "dispatch": dispatch}
