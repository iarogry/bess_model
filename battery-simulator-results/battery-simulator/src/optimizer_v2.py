"""
OPTIMIZER V2: Energy Cascade with Dual Pricing
- Correct SoC tracking (charge → discharge → charge)
- Dual pricing: P_buy (from grid) ≠ P_sell (to grid)
- Energy cascade: Own → Battery → Grid → Sell excess
- Track energy source (for tariff logic)
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data.db"


class DualPricing:
    """Represents asymmetric grid pricing"""
    
    def __init__(self, p_rdn_hrn: float, p_distribution_hrn: float = 0, p_transport_hrn: float = 0):
        """
        Args:
            p_rdn_hrn: РДН price (оптовая цена)
            p_distribution_hrn: Distribution tariff
            p_transport_hrn: Transport tariff
        """
        self.p_rdn = p_rdn_hrn
        self.p_distribution = p_distribution_hrn
        self.p_transport = p_transport_hrn
        
        # What we pay when BUYING from grid
        self.p_buy = p_rdn_hrn + p_distribution_hrn + p_transport_hrn
        
        # What we get when SELLING to grid (only РДН, no tariffs subtracted)
        self.p_sell = p_rdn_hrn
        
        # Value of own generation (saved costs when not buying)
        self.p_own = self.p_buy  # Own energy saves us the FULL cost
    
    def __repr__(self):
        return f"DualPricing(buy={self.p_buy:.2f}, sell={self.p_sell:.2f}, own={self.p_own:.2f})"


class EnergyBalance:
    """Hour-by-hour energy balance with source tracking"""
    
    def __init__(self, hour: int, demand_kw: float, pv_available_kw: float, price_rdn: float):
        self.hour = hour
        self.demand_kw = demand_kw
        self.pv_available_kw = pv_available_kw
        
        # Pricing (using typical Ukrainian tariffs as example)
        # Real values should come from user config or RDN data
        self.pricing = DualPricing(
            p_rdn_hrn=price_rdn,
            p_distribution_hrn=1.5,  # typical distribution tariff
            p_transport_hrn=0.8       # typical transport tariff
        )
        
        # Energy sources used (in kW)
        self.pv_used = 0.0
        self.battery_discharge = 0.0
        self.grid_import = 0.0
        
        # Excess energy for storage/sale
        self.battery_charge = 0.0
        self.grid_export = 0.0
        
        # Battery state
        self.soc_before_kwh = 0.0
        self.soc_after_kwh = 0.0
        
        # Revenue tracking
        self.revenue_hrn = 0.0
        self.energy_source = None  # Which source satisfied demand: "own" | "battery" | "grid"
    
    def calculate_balance(self, soc_before_kwh: float, soc_max_kwh: float, 
                         battery_efficiency: float, time_step_hours: float = 1.0):
        """
        Energy cascade dispatch for this hour:
        1. Use own PV generation first (highest value)
        2. Use battery discharge if needed
        3. Import from grid if deficit remains
        4. Charge battery if surplus (only after satisfying demand)
        5. Export excess to grid (last resort)
        """
        self.soc_before_kwh = soc_before_kwh
        
        # Step 1: Cover demand with PV
        pv_used = min(self.pv_available_kw, self.demand_kw)
        demand_remaining = self.demand_kw - pv_used
        
        # Step 2: Cover remaining demand with battery
        battery_discharge = 0.0
        if demand_remaining > 0 and soc_before_kwh > 0:
            # Can discharge at most (soc_before / time_step) kW
            max_discharge = soc_before_kwh / time_step_hours
            battery_discharge = min(demand_remaining, max_discharge)
            demand_remaining -= battery_discharge
        
        # Step 3: Cover remaining deficit from grid
        grid_import = max(0, demand_remaining)
        
        # Step 4: Calculate available PV surplus after satisfying demand
        pv_surplus = self.pv_available_kw - pv_used  # kW available
        
        # Calculate SoC after demand is met (before charging)
        discharge_kwh = battery_discharge * time_step_hours
        soc_after_demand = soc_before_kwh - discharge_kwh
        
        battery_charge = 0.0
        grid_export = 0.0
        
        if pv_surplus > 0:
            # Available space in battery
            max_charge_kwh = soc_max_kwh - soc_after_demand
            max_charge_kw = max_charge_kwh / time_step_hours
            
            # Charge battery from PV surplus
            charge_kw = min(pv_surplus, max_charge_kw)
            charge_kwh = charge_kw * time_step_hours
            
            # Store in battery with efficiency loss
            stored_kwh = charge_kwh * battery_efficiency
            soc_after_demand += stored_kwh
            battery_charge = charge_kw
            
            # Export remaining surplus
            remaining_surplus = pv_surplus - charge_kw
            grid_export = max(0, remaining_surplus)
        
        # Calculate final SoC
        self.soc_after_kwh = min(soc_max_kwh, max(0, soc_after_demand))
        
        # Revenue calculation
        # Units: kW × hours / 1000 = MWh, then × price_hrn/MWh = hrn
        time_step_hours = 1.0
        
        revenue_from_own = (pv_used * time_step_hours / 1000) * self.pricing.p_own  # Positive (saved costs)
        revenue_from_battery = (battery_discharge * time_step_hours / 1000) * self.pricing.p_own  # Positive (saved costs)
        cost_of_import = (grid_import * time_step_hours / 1000) * self.pricing.p_buy  # Negative
        revenue_from_export = (grid_export * time_step_hours / 1000) * self.pricing.p_sell  # Positive (but low)
        
        self.revenue_hrn = (
            revenue_from_own + 
            revenue_from_battery - 
            cost_of_import + 
            revenue_from_export
        )
        
        # Store final values
        self.pv_used = pv_used
        self.battery_discharge = battery_discharge
        self.grid_import = grid_import
        self.battery_charge = battery_charge
        self.grid_export = grid_export
        
        # Determine energy source priority
        if pv_used > 0:
            self.energy_source = "own"
        elif battery_discharge > 0:
            self.energy_source = "battery"
        else:
            self.energy_source = "grid"
        
        return self.revenue_hrn


class Optimizer24hV2:
    """24-hour rolling window optimizer with energy cascade"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
    
    def _get_day_prices(self, date: str) -> List[float]:
        """Load daily price from database and generate hourly profile"""
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
                # Generate hourly profile from daily price
                return self._generate_hourly_prices(daily_price)
            else:
                # Fallback: realistic seasonal prices
                return self._get_default_prices(date)
        finally:
            conn.close()
    
    def _generate_hourly_prices(self, daily_price: float) -> List[float]:
        """Generate hourly price profile from daily average"""
        # Daily pattern: low night, high day
        return [
            daily_price * 0.7 if h < 6 else         # Night (0-6): 70% of base
            daily_price * 1.3 if 10 <= h < 16 else  # Peak (10-16): 130% of base
            daily_price * 0.9 if 16 <= h < 22 else  # Evening (16-22): 90% of base
            daily_price * 0.7                        # Late night (22-24): 70% of base
            for h in range(24)
        ]
    
    def _get_default_prices(self, date: str) -> List[float]:
        """Fallback: seasonal prices when data unavailable"""
        from datetime import datetime
        
        month = datetime.strptime(date, "%Y-%m-%d").month
        
        # Winter (high), Summer (low)
        base_prices = {
            12: 3500, 1: 3800, 2: 3600,  # Winter
            3: 2800, 4: 2500, 5: 2300,   # Spring
            6: 2100, 7: 2000, 8: 2100,   # Summer
            9: 2400, 10: 2700, 11: 3200  # Fall
        }
        
        base = base_prices.get(month, 2500)
        
        # Daily pattern: low night, high day
        return [
            base * 0.7 if h < 6 else         # Night (0-6): 70% of base
            base * 1.3 if 10 <= h < 16 else  # Peak (10-16): 130% of base
            base * 0.9 if 16 <= h < 22 else  # Evening (16-22): 90% of base
            base * 0.7                        # Late night (22-24): 70% of base
            for h in range(24)
        ]
    
    def _get_demand_profile(self, date: str) -> List[float]:
        """Load daily demand from database and generate hourly profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT demand_kw FROM demand 
                WHERE date = ? AND hour = 24
                LIMIT 1
            """, (date,))
            
            result = cursor.fetchone()
            if result:
                daily_demand = result[0]
                # Generate hourly profile from daily demand
                return self._generate_hourly_demand(daily_demand)
            else:
                # Fallback: typical industrial profile
                return [
                    400 + 100 * (h // 6) if h < 18 else 400  # kW demand per hour
                    for h in range(24)
                ]
        finally:
            conn.close()
    
    def _generate_hourly_demand(self, daily_demand_kw: float) -> List[float]:
        """Generate hourly demand profile from daily total"""
        # Typical industrial: higher day, lower night
        # Assume 16 hours of high load, 8 hours of low load
        hourly_factor = [
            0.5 if h < 6 else               # Night (0-6): 50% of average
            1.2 if 6 <= h < 18 else         # Day (6-18): 120% of average
            0.8                             # Evening (18-24): 80% of average
            for h in range(24)
        ]
        
        # Normalize so total = daily_demand
        sum_factor = sum(hourly_factor)
        avg_per_hour = daily_demand_kw / 24.0
        
        return [factor * avg_per_hour / (sum_factor / 24.0) for factor in hourly_factor]
    
    def _get_pv_profile(self, date: str) -> List[float]:
        """Load or generate hourly PV generation"""
        from datetime import datetime
        
        day_of_year = datetime.strptime(date, "%Y-%m-%d").timetuple().tm_yday
        
        # Simplified: sine wave based on day of year
        # Peak in summer (~day 172 = June 21)
        import math
        seasonal_factor = 0.5 + 0.5 * math.sin((day_of_year - 80) * 3.14159 / 365)
        
        # Daily profile: bell curve, peak at noon
        max_capacity_kw = 2500
        return [
            max_capacity_kw * seasonal_factor * max(0, math.sin((h - 6) * 3.14159 / 12))
            if 6 <= h <= 18 else 0
            for h in range(24)
        ]
    
    def optimize_day(self, date: str, initial_soc_kwh: float = 2500.0, 
                    battery_capacity_kwh: float = 5000.0,
                    battery_efficiency: float = 0.95) -> Dict:
        """
        Optimize single day using energy cascade
        
        Args:
            date: "2025-05-10"
            initial_soc_kwh: Starting battery state
            battery_capacity_kwh: Max battery capacity
            battery_efficiency: Round-trip efficiency
        
        Returns:
            {
                "date": "2025-05-10",
                "total_revenue": 12345.67,
                "dispatch": [
                    {
                        "hour": 0,
                        "price_rdn": 2500,
                        "demand": 400,
                        "pv_available": 0,
                        "pv_used": 0,
                        "battery_discharge": 0,
                        "grid_import": 400,
                        "battery_charge": 0,
                        "grid_export": 0,
                        "soc_before": 2500,
                        "soc_after": 2500,
                        "revenue": -1000,
                        "energy_source": "grid"
                    },
                    ...
                ]
            }
        """
        prices = self._get_day_prices(date)
        demand = self._get_demand_profile(date)
        pv = self._get_pv_profile(date)
        
        dispatch = []
        total_revenue = 0.0
        current_soc = initial_soc_kwh
        
        for hour in range(24):
            balance = EnergyBalance(
                hour=hour,
                demand_kw=demand[hour],
                pv_available_kw=pv[hour],
                price_rdn=prices[hour]
            )
            
            revenue = balance.calculate_balance(
                soc_before_kwh=current_soc,
                soc_max_kwh=battery_capacity_kwh,
                battery_efficiency=battery_efficiency,
                time_step_hours=1.0
            )
            
            total_revenue += revenue
            current_soc = balance.soc_after_kwh
            
            dispatch.append({
                "hour": hour,
                "price_rdn": prices[hour],
                "demand": demand[hour],
                "pv_available": pv[hour],
                "pv_used": balance.pv_used,
                "battery_discharge": balance.battery_discharge,
                "grid_import": balance.grid_import,
                "battery_charge": balance.battery_charge,
                "grid_export": balance.grid_export,
                "soc_before": balance.soc_before_kwh,
                "soc_after": balance.soc_after_kwh,
                "revenue": revenue,
                "energy_source": balance.energy_source,
                "pricing": {
                    "p_buy": balance.pricing.p_buy,
                    "p_sell": balance.pricing.p_sell,
                    "p_own": balance.pricing.p_own
                }
            })
        
        logger.info(f"Day {date}: Revenue = {total_revenue:,.2f} грн | Final SoC = {current_soc:.1f} kWh")
        
        return {
            "date": date,
            "total_revenue": total_revenue,
            "final_soc": current_soc,
            "dispatch": dispatch,
            "battery_cycles": sum(1 for h in dispatch if h["battery_charge"] > 0) / 24.0
        }
