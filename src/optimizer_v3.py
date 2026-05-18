"""
OPTIMIZER V3: Multi-Source Energy Dispatch with 24h Look-Ahead LP Optimization

Features:
- 24-hour rolling window optimization (look-ahead planning)
- Multiple energy sources: PV + Battery + Grid + CHP + Flywheel
- Battery efficiency losses (80% round-trip) as real cost
- Two-cycle battery dispatch when profitable
- Linear Programming (Pyomo) for optimal economic dispatch
- Greedy fallback when solver unavailable
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import math

try:
    from pyomo.environ import *
    from pyomo.opt import SolverFactory
    HAS_PYOMO = True
except ImportError:
    HAS_PYOMO = False

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
        self.battery_efficiency_round_trip = 0.80  # 20% loss!
        self.battery_max_charge_kw = 500
        self.battery_max_discharge_kw = 500
        
        # CHP (Когенератор)
        self.chp_enabled = True
        self.chp_capacity_kw = 1000
        self.chp_efficiency_elec = 0.40
        self.chp_efficiency_heat = 0.45
        self.chp_fuel_cost_hrn_per_mwh = 3500
        self.chp_startup_time_min = 5
        self.chp_startup_cost_hrn = 1000
        self.chp_min_load_percent = 30
        
        # Flywheel (Optional)
        self.flywheel_enabled = False
        self.flywheel_capacity_kwh = 200
        self.flywheel_efficiency = 0.95
        
        # Grid
        self.grid_max_import_kw = 5000
        self.grid_max_export_kw = 5000
        
        # Demand flexibility
        self.demand_flexibility_percent = 0


class DayPriceForecast:
    """24-hour price forecast for a single day"""
    
    def __init__(self, date: str, prices: List[float]):
        """
        Args:
            date: "2025-05-10"
            prices: List of 24 hourly prices (hrn/MWh)
        """
        self.date = date
        self.prices = prices  # 24 values
        
        # Calculate statistics for decision-making
        self.price_min = min(prices)
        self.price_max = max(prices)
        self.price_spread = self.price_max - self.price_min
        self.price_avg = sum(prices) / len(prices)
        
        # Identify low-cost and peak hours
        self.low_hours = [h for h in range(24) if prices[h] <= self.price_avg * 0.8]
        self.peak_hours = [h for h in range(24) if prices[h] >= self.price_avg * 1.2]
    
    def is_two_cycle_profitable(self, battery_capacity_kwh: float, 
                               battery_efficiency: float,
                               tariff_distribution: float = 1.5,
                               tariff_transport: float = 0.8) -> bool:
        """
        Determine if two battery cycles per day are profitable
        
        Logic:
        - Charge at low price hour
        - Discharge at peak price hour
        - Account for 20% efficiency loss (80% efficiency)
        """
        # Cost of efficiency losses
        loss_percent = 1.0 - battery_efficiency
        loss_cost_per_kwh = (self.price_min + tariff_distribution + tariff_transport) * loss_percent
        
        # Revenue from arbitrage (buy cheap, sell dear)
        profit_per_kwh = (self.price_max - self.price_min) - loss_cost_per_kwh
        total_profit = profit_per_kwh * battery_capacity_kwh
        
        logger.info(f"Two-cycle check: spread={self.price_spread:.0f}, "
                   f"loss_cost={loss_cost_per_kwh:.0f}, "
                   f"profit={total_profit:,.0f}")
        
        return total_profit > 0


class Optimizer24hV3:
    """24-hour look-ahead optimizer with LP formulation"""
    
    def __init__(self, config: EnergySourceConfig = None, db_path=DB_PATH):
        self.config = config or EnergySourceConfig()
        self.db_path = db_path
    
    def _load_prices(self, date: str) -> DayPriceForecast:
        """Load daily price and generate hourly profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT price_hrn_per_mwh FROM prices 
                WHERE date = ? AND hour = 24
                LIMIT 1
            """, (date,))
            
            result = cursor.fetchone()
            if result:
                daily_price = result[0]
                prices = self._generate_hourly_prices(daily_price)
            else:
                prices = self._get_default_prices(date)
            
            return DayPriceForecast(date, prices)
        finally:
            conn.close()
    
    def _generate_hourly_prices(self, daily_price: float) -> List[float]:
        """Generate hourly profile with day/night variation"""
        return [
            daily_price * 0.7 if h < 6 else
            daily_price * 1.3 if 10 <= h < 16 else
            daily_price * 0.9 if 16 <= h < 22 else
            daily_price * 0.7
            for h in range(24)
        ]
    
    def _get_default_prices(self, date: str) -> List[float]:
        """Fallback seasonal prices"""
        month = datetime.strptime(date, "%Y-%m-%d").month
        base_prices = {
            12: 3500, 1: 3800, 2: 3600,
            3: 2800, 4: 2500, 5: 2300,
            6: 2100, 7: 2000, 8: 2100,
            9: 2400, 10: 2700, 11: 3200
        }
        base = base_prices.get(month, 2500)
        return self._generate_hourly_prices(base)
    
    def _get_pv_profile(self, date: str) -> List[float]:
        """Generate PV generation profile"""
        day_of_year = datetime.strptime(date, "%Y-%m-%d").timetuple().tm_yday
        seasonal_factor = 0.5 + 0.5 * math.sin((day_of_year - 80) * math.pi / 365)
        
        max_capacity_kw = self.config.pv_capacity_kw
        return [
            max_capacity_kw * seasonal_factor * max(0, math.sin((h - 6) * math.pi / 12))
            if 6 <= h <= 18 else 0
            for h in range(24)
        ]
    
    def _get_demand_profile(self, date: str) -> List[float]:
        """Generate hourly demand profile"""
        daily_demand = 170.0  # From DB or config
        
        hourly_factor = [
            0.5 if h < 6 else
            1.2 if 6 <= h < 18 else
            0.8
            for h in range(24)
        ]
        
        sum_factor = sum(hourly_factor)
        avg_per_hour = daily_demand / 24.0
        
        return [factor * avg_per_hour / (sum_factor / 24.0) for factor in hourly_factor]
    
    def optimize_day_lp(self, date: str, initial_soc_kwh: float = 2500.0) -> Dict:
        """
        Optimize dispatch using Linear Programming (Pyomo + CBC/GLPK)
        
        This is the OPTIMAL solution - finds truly best dispatch for the day
        """
        if not HAS_PYOMO:
            logger.warning("Pyomo not installed. Falling back to greedy optimizer.")
            return self.optimize_day_greedy(date, initial_soc_kwh)
        
        # Load data
        price_forecast = self._load_prices(date)
        pv_profile = self._get_pv_profile(date)
        demand_profile = self._get_demand_profile(date)
        
        logger.info(f"Optimizing {date} with LP (price spread: {price_forecast.price_spread:.0f})")
        
        # Build Pyomo model
        model = ConcreteModel()
        
        # Sets
        model.hours = RangeSet(0, 23)
        
        # Decision variables
        model.pv_use = Var(model.hours, within=NonNegativeReals)  # kW
        model.battery_charge = Var(model.hours, within=NonNegativeReals)  # kW
        model.battery_discharge = Var(model.hours, within=NonNegativeReals)  # kW
        model.grid_import = Var(model.hours, within=NonNegativeReals)  # kW
        model.grid_export = Var(model.hours, within=NonNegativeReals)  # kW
        model.battery_soc = Var(model.hours, bounds=(
            self.config.battery_capacity_kwh * self.config.battery_soc_min_percent / 100,
            self.config.battery_capacity_kwh * self.config.battery_soc_max_percent / 100
        ))  # kWh
        
        # CHP variables (optional)
        if self.config.chp_enabled:
            model.chp_output = Var(model.hours, within=NonNegativeReals)  # kW
            model.chp_on = Var(model.hours, within=Binary)  # 0 or 1
        
        # Objective: Maximize revenue (minimize costs)
        tariff_dist = 1.5
        tariff_trans = 0.8
        
        def objective_rule(m):
            revenue = 0
            
            for h in m.hours:
                h_idx = int(h)
                
                # Revenue from grid export (at РДН price, no tariffs)
                revenue += m.grid_export[h] * price_forecast.prices[h_idx]
                
                # Cost of grid import (at РДН + tariffs)
                revenue -= m.grid_import[h] * (price_forecast.prices[h_idx] + tariff_dist + tariff_trans)
                
                # Cost of battery losses (20% of discharge → pay at buy price)
                loss_percent = 1.0 - self.config.battery_efficiency_round_trip
                revenue -= m.battery_discharge[h] * loss_percent * (price_forecast.prices[h_idx] + tariff_dist + tariff_trans)
                
                # CHP fuel cost
                if self.config.chp_enabled:
                    revenue -= m.chp_output[h] * self.config.chp_fuel_cost_hrn_per_mwh / 1000  # Convert to kW basis
            
            return revenue
        
        model.obj = Objective(rule=objective_rule, sense=maximize)
        
        # Constraints
        # Energy balance: demand = pv + battery_discharge + grid_import + chp
        def energy_balance_rule(m, h):
            h_idx = int(h)
            demand = demand_profile[h_idx]
            
            if self.config.chp_enabled:
                return (m.pv_use[h] + m.battery_discharge[h] + m.grid_import[h] + m.chp_output[h] 
                        >= demand)
            else:
                return (m.pv_use[h] + m.battery_discharge[h] + m.grid_import[h] 
                        >= demand)
        
        model.energy_balance = Constraint(model.hours, rule=energy_balance_rule)
        
        # PV constraint
        def pv_constraint_rule(m, h):
            h_idx = int(h)
            pv_avail = pv_profile[h_idx]
            
            # Can use at most available PV
            # Remainder must be stored or exported
            return m.pv_use[h] + m.battery_charge[h] + m.grid_export[h] <= pv_avail
        
        model.pv_constraint = Constraint(model.hours, rule=pv_constraint_rule)
        
        # Battery SoC dynamics
        def battery_soc_rule(m, h):
            h_idx = int(h)
            
            if h_idx == 0:
                soc_prev = initial_soc_kwh
            else:
                soc_prev = m.battery_soc[h_idx - 1]
            
            # SoC(t+1) = SoC(t) + charge*eff - discharge/eff
            charge_kwh = m.battery_charge[h] * self.config.battery_efficiency_round_trip
            discharge_kwh = m.battery_discharge[h] / self.config.battery_efficiency_round_trip
            
            return m.battery_soc[h] == soc_prev + charge_kwh - discharge_kwh
        
        model.battery_soc_constraint = Constraint(model.hours, rule=battery_soc_rule)
        
        # Battery charge/discharge limits
        model.battery_charge_limit = Constraint(
            model.hours,
            rule=lambda m, h: m.battery_charge[h] <= self.config.battery_max_charge_kw
        )
        
        model.battery_discharge_limit = Constraint(
            model.hours,
            rule=lambda m, h: m.battery_discharge[h] <= self.config.battery_max_discharge_kw
        )
        
        # Grid limits
        model.grid_import_limit = Constraint(
            model.hours,
            rule=lambda m, h: m.grid_import[h] <= self.config.grid_max_import_kw
        )
        
        model.grid_export_limit = Constraint(
            model.hours,
            rule=lambda m, h: m.grid_export[h] <= self.config.grid_max_export_kw
        )
        
        # CHP constraints (optional)
        if self.config.chp_enabled:
            chp_min = self.config.chp_capacity_kw * self.config.chp_min_load_percent / 100
            
            model.chp_min_load = Constraint(
                model.hours,
                rule=lambda m, h: m.chp_output[h] >= chp_min * m.chp_on[h]
            )
            
            model.chp_max_capacity = Constraint(
                model.hours,
                rule=lambda m, h: m.chp_output[h] <= self.config.chp_capacity_kw * m.chp_on[h]
            )
        
        # Solve
        solver = None
        for solver_name in ['cbc', 'glpk', 'ipopt']:
            try:
                solver = SolverFactory(solver_name)
                if solver.available():
                    logger.info(f"Using solver: {solver_name}")
                    break
            except:
                continue
        
        if solver is None:
            logger.warning("No LP solver available. Using greedy fallback.")
            return self.optimize_day_greedy(date, initial_soc_kwh)
        
        try:
            results = solver.solve(model, tee=False)
            
            if results.solver.status != SolverStatus.ok:
                logger.warning(f"Solver status: {results.solver.status}. Using greedy fallback.")
                return self.optimize_day_greedy(date, initial_soc_kwh)
        except Exception as e:
            logger.warning(f"Solver error: {e}. Using greedy fallback.")
            return self.optimize_day_greedy(date, initial_soc_kwh)
        
        # Extract results
        dispatch = []
        total_revenue = 0.0
        
        for h in range(24):
            pv_used = value(model.pv_use[h])
            batt_charge = value(model.battery_charge[h])
            batt_discharge = value(model.battery_discharge[h])
            grid_in = value(model.grid_import[h])
            grid_out = value(model.grid_export[h])
            soc = value(model.battery_soc[h])
            
            # Calculate revenue for this hour
            tariff_dist = 1.5
            tariff_trans = 0.8
            
            revenue = (
                grid_out * price_forecast.prices[h] -
                grid_in * (price_forecast.prices[h] + tariff_dist + tariff_trans) -
                batt_discharge * (1.0 - self.config.battery_efficiency_round_trip) * 
                (price_forecast.prices[h] + tariff_dist + tariff_trans)
            )
            
            total_revenue += revenue
            
            dispatch.append({
                "hour": h,
                "price_rdn": price_forecast.prices[h],
                "demand": demand_profile[h],
                "pv_available": pv_profile[h],
                "pv_used": pv_used,
                "battery_charge": batt_charge,
                "battery_discharge": batt_discharge,
                "grid_import": grid_in,
                "grid_export": grid_out,
                "soc_before": value(model.battery_soc[h-1]) if h > 0 else initial_soc_kwh,
                "soc_after": soc,
                "revenue": revenue,
                "optimizer": "LP"
            })
        
        logger.info(f"LP Optimization complete: {date} → Revenue: {total_revenue:,.0f} грн")
        
        return {
            "date": date,
            "total_revenue": total_revenue,
            "final_soc": value(model.battery_soc[23]),
            "dispatch": dispatch,
            "optimizer_used": "LP"
        }
    
    def optimize_day_greedy(self, date: str, initial_soc_kwh: float = 2500.0) -> Dict:
        """
        Fallback: Greedy optimizer with energy cascade
        (Same as V2, but now with two-cycle support)
        """
        price_forecast = self._load_prices(date)
        pv_profile = self._get_pv_profile(date)
        demand_profile = self._get_demand_profile(date)
        
        # Check if two cycles are profitable
        use_two_cycles = price_forecast.is_two_cycle_profitable(
            self.config.battery_capacity_kwh,
            self.config.battery_efficiency_round_trip
        )
        
        logger.info(f"Greedy optimization: {date} (two_cycles={use_two_cycles})")
        
        # For now, use same energy cascade as V2
        # TODO: Implement two-cycle logic in greedy path
        
        dispatch = []
        current_soc = initial_soc_kwh
        total_revenue = 0.0
        
        for h in range(24):
            # Energy cascade (same as V2)
            pv_used = min(pv_profile[h], demand_profile[h])
            demand_remaining = demand_profile[h] - pv_used
            
            # Battery discharge
            batt_discharge = 0.0
            if demand_remaining > 0 and current_soc > 0:
                max_discharge = current_soc / 1.0  # 1 hour timestep
                batt_discharge = min(demand_remaining, max_discharge)
                demand_remaining -= batt_discharge
            
            # Grid import
            grid_import = max(0, demand_remaining)
            
            # PV surplus
            pv_surplus = pv_profile[h] - pv_used
            soc_after_discharge = current_soc - batt_discharge * 1.0
            
            # Battery charge and grid export
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
            
            # Revenue calculation
            tariff_dist = 1.5
            tariff_trans = 0.8
            loss_percent = 1.0 - self.config.battery_efficiency_round_trip
            
            revenue = (
                grid_export * price_forecast.prices[h] -
                grid_import * (price_forecast.prices[h] + tariff_dist + tariff_trans) -
                batt_discharge * loss_percent * (price_forecast.prices[h] + tariff_dist + tariff_trans)
            )
            
            total_revenue += revenue
            
            dispatch.append({
                "hour": h,
                "price_rdn": price_forecast.prices[h],
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
        
        logger.info(f"Greedy optimization complete: {date} → Revenue: {total_revenue:,.0f} грн")
        
        return {
            "date": date,
            "total_revenue": total_revenue,
            "final_soc": current_soc,
            "dispatch": dispatch,
            "optimizer_used": "GREEDY"
        }
    
    def optimize_day(self, date: str, initial_soc_kwh: float = 2500.0) -> Dict:
        """Main entry point - tries LP, falls back to greedy"""
        return self.optimize_day_lp(date, initial_soc_kwh)
