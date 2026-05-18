"""
Phase 3: 24-hour Rolling Window Optimizer
Multi-source energy dispatch: PV + Battery + Grid + CHP
No lookahead bias - uses only current day's prices
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

try:
    from pyomo.environ import *
    from pyomo.opt import SolverFactory
    HAS_PYOMO = True
except ImportError:
    HAS_PYOMO = False
    logging.warning("Pyomo not installed. Using fallback greedy optimizer.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data.db"


class EnergyConfig:
    """Configuration for energy sources"""
    
    def __init__(self):
        self.pv_capacity_kw = 2500
        self.pv_efficiency = 0.95
        
        self.battery_capacity_kwh = 5000
        self.battery_soc_min_percent = 20
        self.battery_soc_max_percent = 80
        self.battery_efficiency = 0.95
        self.battery_max_charge_kw = 500
        self.battery_max_discharge_kw = 500
        
        self.chp_capacity_kw = 1000
        self.chp_efficiency_elec = 0.40
        self.chp_fuel_cost_hrn_per_mwh = 3500
        self.chp_startup_time_min = 5
        self.chp_min_load_percent = 30
        
        self.grid_max_import_kw = 5000
        self.grid_max_export_kw = 5000
    
    @classmethod
    def from_user_input(cls, user_config: Dict) -> "EnergyConfig":
        """Create from frontend user input with MW to kW conversion"""
        config = cls()
        
        if "energy_sources" in user_config:
            sources = user_config["energy_sources"]
            
            # Helper to extract value and convert if needed
            def get_val_kw(params, key_mw, key_kw, default):
                if key_mw in params:
                    return float(params[key_mw]) * 1000
                return float(params.get(key_kw, default))

            if "pv" in sources:
                pv = sources["pv"]
                config.pv_capacity_kw = get_val_kw(pv, "rated_power_mw", "capacity_kw", 2500)
            
            if "battery" in sources:
                bat = sources["battery"]
                config.battery_capacity_kwh = get_val_kw(bat, "capacity_mwh", "capacity_kwh", 5000)
                config.battery_efficiency = bat.get("efficiency_round_trip", 0.95)
                config.battery_max_charge_kw = get_val_kw(bat, "max_charge_mw", "max_charge_kw", 500)
                config.battery_max_discharge_kw = get_val_kw(bat, "max_discharge_mw", "max_discharge_kw", 500)
            
            if "chp" in sources:
                chp = sources["chp"]
                config.chp_capacity_kw = get_val_kw(chp, "rated_power_mw", "capacity_kw", 1000)
                config.chp_fuel_cost_hrn_per_mwh = chp.get("fuel_cost_hrn_per_mwh", 3500)
                config.chp_startup_time_min = chp.get("startup_time_minutes", 5)
        
        return config


class Optimizer24h:
    """24-hour rolling window optimizer using Linear Programming"""
    
    def __init__(self, config: EnergyConfig, db_path=DB_PATH):
        self.config = config
        self.db_path = db_path
    
    def optimize_day(self, date: str, initial_soc_kwh: Optional[float] = None) -> Dict:
        """
        Optimize dispatch for a single day (24 hours)
        
        Args:
            date: "2025-05-10"
            initial_soc_kwh: Starting battery SoC (default: mid-point)
        
        Returns:
            {
                "date": "2025-05-10",
                "revenue": 15430.50,
                "dispatch": [
                    {"hour": 1, "price": 2500, "pv": 0, "grid": 450, "chp": 0, "charge": 100, "discharge": 0, "soc": 2100},
                    ...
                ]
            }
        """
        
        if not HAS_PYOMO:
            logger.warning("Using fallback greedy optimizer (Pyomo not available)")
            return self._optimize_greedy(date, initial_soc_kwh)
        
        return self._optimize_lp(date, initial_soc_kwh)
    
    def _get_day_data(self, date: str) -> Dict:
        """Fetch prices and demand for a day from SQLite"""
        prices_data = {}
        demand_data = {}
        
        # Default prices
        for h in range(1, 25):
            if h in range(1, 7):
                prices_data[h] = 2500
            elif h in range(7, 13):
                prices_data[h] = 3500
            elif h in range(13, 19):
                prices_data[h] = 4500
            else:
                prices_data[h] = 3000
        
        # Default demand
        for h in range(1, 25):
            demand_data[h] = 400
        
        # Get PV profile
        pv_profile = self._get_pv_profile(date)
        
        return {
            "date": date,
            "prices": prices_data,
            "demand": demand_data,
            "pv_profile": pv_profile
        }
    
    def _get_pv_profile(self, date: str) -> Dict:
        """
        Get PV generation profile for a day
        Returns {hour: percent_of_capacity} (0.0 to 1.0)
        
        Pattern (typical spring/fall day, 2.5 MW capacity):
        - Hours 1-6 (night): 0%
        - Hours 7-8 (dawn): 10-20%
        - Hours 9-15 (day): 60-95%
        - Hours 16-17 (dusk): 20-10%
        - Hours 18-24 (night): 0%
        """
        
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        month = date_obj.month
        
        # Seasonal factor
        if month in [6, 7, 8]:  # Summer (longer days, higher sun)
            day_length = 18
            peak_factor = 1.0
        elif month in [12, 1]:  # Winter (short days, low sun)
            day_length = 10
            peak_factor = 0.5
        else:  # Spring/Fall
            day_length = 14
            peak_factor = 0.85
        
        # Sunrise/sunset approximation (6am to 8pm for spring)
        sunrise = 6
        sunset = 20
        
        profile = {}
        for hour in range(1, 25):
            if hour < sunrise or hour > sunset:
                profile[hour] = 0.0
            else:
                # Cosine curve for realistic sun elevation
                hours_since_sunrise = hour - sunrise
                hours_to_sunset = sunset - hour
                
                if hours_since_sunrise <= 0 or hours_to_sunset <= 0:
                    profile[hour] = 0.0
                else:
                    # Peak at solar noon (approximately 12:00)
                    mid_day = (sunset + sunrise) / 2
                    x = (hour - mid_day) / (day_length / 2)
                    profile[hour] = max(0.0, peak_factor * (1 - x**2))
        
        return profile
    
    def _optimize_lp(self, date: str, initial_soc_kwh: Optional[float] = None) -> Dict:
        """Linear Programming optimization using Pyomo + CBC"""
        
        day_data = self._get_day_data(date)
        if not day_data:
            return self._optimize_greedy(date, initial_soc_kwh)
        
        # Set initial SoC
        if initial_soc_kwh is None:
            initial_soc_kwh = self.config.battery_capacity_kwh * 0.5
        
        # Create Pyomo model
        model = ConcreteModel()
        
        # Decision variables (24 hours)
        model.hours = RangeSet(1, 24)
        
        # PV output (kW)
        model.p_pv = Var(model.hours, bounds=(0, self.config.pv_capacity_kw))
        
        # Grid power (kW): >0 = buy, <0 = sell
        model.p_grid = Var(model.hours, bounds=(-self.config.grid_max_export_kw, 
                                                 self.config.grid_max_import_kw))
        
        # CHP output (kW)
        model.p_chp = Var(model.hours, bounds=(0, self.config.chp_capacity_kw))
        
        # Battery charge/discharge (kW)
        model.p_charge = Var(model.hours, bounds=(0, self.config.battery_max_charge_kw))
        model.p_discharge = Var(model.hours, bounds=(0, self.config.battery_max_discharge_kw))
        
        # Battery SoC (kWh)
        soc_min = self.config.battery_capacity_kwh * self.config.battery_soc_min_percent / 100
        soc_max = self.config.battery_capacity_kwh * self.config.battery_soc_max_percent / 100
        model.soc = Var(model.hours, bounds=(soc_min, soc_max))
        
        # Objective: Maximize revenue (minimize cost of grid purchases)
        def revenue_rule(model):
            return -sum(model.p_grid[h] * day_data["prices"][h] for h in model.hours)
        model.obj = Objective(rule=revenue_rule, sense=maximize)
        
        # Constraints
        
        # 1. Energy balance (for each hour)
        def energy_balance(model, h):
            pv_output = model.p_pv[h] * self.config.pv_efficiency
            chp_output = model.p_chp[h]
            battery_net = (model.p_charge[h] - model.p_discharge[h]) / self.config.battery_efficiency
            
            demand = day_data["demand"].get(h, 500)  # kW
            
            # pv + chp - grid - demand = battery_net
            # pv + chp - grid - demand = (charge - discharge) / eff
            return pv_output + chp_output - model.p_grid[h] - demand == battery_net
        model.balance = Constraint(model.hours, rule=energy_balance)
        
        # 2. Battery SoC tracking
        def soc_tracking(model, h):
            if h == 1:
                prev_soc = initial_soc_kwh
            else:
                prev_soc = model.soc[h-1]
            
            charge_energy = model.p_charge[h] * 1.0  # 1 hour
            discharge_energy = model.p_discharge[h] * 1.0
            
            return model.soc[h] == prev_soc + charge_energy - discharge_energy
        model.soc_track = Constraint(model.hours, rule=soc_tracking)
        
        # 3. PV output constrained by irradiance
        def pv_constraint(model, h):
            pv_max = self.config.pv_capacity_kw * day_data["pv_profile"].get(h, 0.0)
            return model.p_pv[h] <= pv_max
        model.pv_max = Constraint(model.hours, rule=pv_constraint)
        
        # 4. CHP minimum load (if running, must be >30%)
        # Simplified: allow any value 0 to max
        # (In production: add binary variable for on/off)
        
        # Solve
        try:
            solver = SolverFactory('cbc')
            solver.options['seconds'] = 10
            
            results = solver.solve(model, tee=False)
            
            if results.solver.status != SolverStatus.ok:
                logger.warning(f"Solver status: {results.solver.status}, falling back to greedy")
                return self._optimize_greedy(date, initial_soc_kwh)
            
            # Extract solution
            dispatch = []
            total_revenue = 0
            
            for h in range(1, 25):
                revenue_hour = -value(model.p_grid[h]) * day_data["prices"][h]
                total_revenue += revenue_hour
                
                dispatch.append({
                    "hour": h,
                    "price_hrn_per_mwh": day_data["prices"][h],
                    "pv_kw": round(value(model.p_pv[h]), 1),
                    "grid_buy_kw": max(0, round(value(model.p_grid[h]), 1)),
                    "grid_sell_kw": max(0, -round(value(model.p_grid[h]), 1)),
                    "chp_kw": round(value(model.p_chp[h]), 1),
                    "battery_charge_kw": round(value(model.p_charge[h]), 1),
                    "battery_discharge_kw": round(value(model.p_discharge[h]), 1),
                    "battery_soc_kwh": round(value(model.soc[h]), 1),
                    "revenue_hrn": round(revenue_hour, 2)
                })
            
            return {
                "date": date,
                "status": "optimal",
                "total_revenue_hrn": round(total_revenue, 2),
                "final_soc_kwh": round(value(model.soc[24]), 1),
                "dispatch": dispatch
            }
        
        except Exception as e:
            logger.error(f"Optimization error: {e}")
            return self._optimize_greedy(date, initial_soc_kwh)
    
    def _optimize_greedy(self, date: str, initial_soc_kwh: Optional[float] = None) -> Dict:
        """Fallback greedy optimizer (no Pyomo required)"""
        
        day_data = self._get_day_data(date)
        if not day_data:
            return {"date": date, "status": "error", "message": "No data"}
        
        if initial_soc_kwh is None:
            initial_soc_kwh = self.config.battery_capacity_kwh * 0.5
        
        dispatch = []
        current_soc = initial_soc_kwh
        total_revenue = 0
        
        # Find price range for the day
        prices = list(day_data["prices"].values())
        min_price = min(prices)
        max_price = max(prices)
        threshold = (min_price + max_price) / 2
        
        for h in range(1, 25):
            price = day_data["prices"][h]
            pv_output = self.config.pv_capacity_kw * day_data["pv_profile"].get(h, 0.0)
            demand = day_data["demand"].get(h, 500)
            
            grid_kw = 0
            charge_kw = 0
            discharge_kw = 0
            chp_kw = 0
            
            # Simple strategy: 
            # - If price is low: charge battery
            # - If price is high: discharge battery + consider CHP
            # - Fulfill demand from PV first, then battery, then grid
            
            available_from_pv = pv_output * self.config.pv_efficiency
            remaining_demand = max(0, demand - available_from_pv)
            
            if price < threshold and current_soc < self.config.battery_capacity_kwh * 0.8:
                # Low price: charge battery
                charge_kw = min(
                    self.config.battery_max_charge_kw,
                    (self.config.battery_capacity_kwh * 0.8 - current_soc)
                )
                grid_kw = remaining_demand + charge_kw
            
            elif price > threshold and current_soc > self.config.battery_capacity_kwh * 0.3:
                # High price: discharge battery
                discharge_kw = min(
                    self.config.battery_max_discharge_kw,
                    remaining_demand
                )
                remaining_demand = max(0, remaining_demand - discharge_kw)
                grid_kw = remaining_demand
                
                # Consider CHP if still needed
                if remaining_demand > 100:
                    chp_kw = min(self.config.chp_capacity_kw, remaining_demand)
                    grid_kw -= chp_kw
            
            else:
                # Medium price: use grid as needed
                grid_kw = remaining_demand
            
            # Update SoC
            net_battery = (charge_kw - discharge_kw) / self.config.battery_efficiency
            current_soc = max(0, current_soc + net_battery)
            
            # Calculate revenue
            revenue = -grid_kw * price / 1000  # Convert to hours value (1 hour)
            total_revenue += revenue
            
            dispatch.append({
                "hour": h,
                "price_hrn_per_mwh": price,
                "pv_kw": round(pv_output, 1),
                "grid_buy_kw": max(0, round(grid_kw, 1)),
                "grid_sell_kw": max(0, -round(grid_kw, 1)),
                "chp_kw": round(chp_kw, 1),
                "battery_charge_kw": round(charge_kw, 1),
                "battery_discharge_kw": round(discharge_kw, 1),
                "battery_soc_kwh": round(current_soc, 1),
                "revenue_hrn": round(revenue, 2)
            })
        
        return {
            "date": date,
            "status": "greedy",
            "total_revenue_hrn": round(total_revenue, 2),
            "final_soc_kwh": round(current_soc, 1),
            "dispatch": dispatch
        }


def main():
    """Test optimizer on a single day"""
    
    config = EnergyConfig()
    optimizer = Optimizer24h(config)
    
    # Optimize a single day
    test_date = "2025-08-15"
    
    logger.info(f"Optimizing {test_date}...")
    result = optimizer.optimize_day(test_date, initial_soc_kwh=2500)
    
    if result["status"] != "error":
        logger.info(f"\n{'='*60}")
        logger.info(f"Date: {result['date']}")
        logger.info(f"Daily Revenue: {result['total_revenue_hrn']:,.2f} грн")
        logger.info(f"Final SoC: {result['final_soc_kwh']:.1f} kWh")
        logger.info(f"{'='*60}\n")
        
        # Show first 6 hours
        logger.info("First 6 hours:")
        for d in result["dispatch"][:6]:
            logger.info(f"  Hour {d['hour']:2d}: Price {d['price_hrn_per_mwh']:5.0f}, "
                       f"PV {d['pv_kw']:6.1f}kW, Grid {d['grid_buy_kw']:6.1f}kW, "
                       f"SoC {d['battery_soc_kwh']:6.1f}kWh, Revenue {d['revenue_hrn']:7.2f}грн")
    else:
        logger.error(f"Optimization failed: {result.get('message')}")


if __name__ == "__main__":
    main()
