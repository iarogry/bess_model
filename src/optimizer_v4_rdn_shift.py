#!/usr/bin/env python3
"""
V4-RDN-SHIFT: 12-Hour Shift Battery Trading Strategy
Correct logic: equal charge/discharge cycles with shift-based price arbitrage
"""

import numpy as np
import json
from datetime import datetime

class V4RDNShift:
    """
    12-hour shift strategy for battery trading:
    - Calculate charge/discharge duration: capacity / power
    - Split day into 2 shifts (00:00-11:59, 12:00-23:59)
    - Per shift: find cheapest N hours to charge, most expensive N hours to discharge
    - Work battery only during these hours
    - If battery insufficient: use grid (requires free grid power)
    """
    
    def __init__(self,
                 rdn_prices_uah_per_mwh,
                 battery_capacity_mwh=10.0,
                 battery_power_mw=2.5,
                 battery_rte=0.88,
                 grid_tariff_uah_per_mwh=784.2):  # 686.23 + 98.97
        """
        Args:
            rdn_prices_uah_per_mwh: array of 8760 hourly prices [UAH/MWh]
            battery_capacity_mwh: battery capacity [MWh]
            battery_power_mw: max charge/discharge power [MW]
            battery_rte: round-trip efficiency
            grid_tariff_uah_per_mwh: grid import tariff [UAH/MWh]
        """
        
        self.prices = np.array(rdn_prices_uah_per_mwh, dtype=float)
        self.battery_capacity_mwh = battery_capacity_mwh
        self.battery_capacity_kwh = battery_capacity_mwh * 1000
        self.battery_power_mw = battery_power_mw
        self.battery_power_kw = battery_power_mw * 1000
        self.battery_rte = battery_rte
        self.grid_tariff = grid_tariff_uah_per_mwh
        
        self.n_hours = len(self.prices)
        
        # Calculate charge/discharge duration
        self.cycle_hours = int(self.battery_capacity_kwh / self.battery_power_kw)
        self.cycle_hours = max(2, min(5, self.cycle_hours))  # Clamp to 2-5 hours
        
        print(f"⚙️  Charge/Discharge Duration: {self.cycle_hours} hours")
        print(f"   Energy per cycle: {self.cycle_hours * self.battery_power_kw:.0f} kWh")
    
    def optimize_shift(self, shift_hours, shift_idx):
        """
        Optimize a 12-hour shift (hours 0-11 or 12-23 per day)
        
        Args:
            shift_hours: list of 12 hourly prices
            shift_idx: 0 for first shift (00:00-11:59), 1 for second (12:00-23:59)
        
        Returns:
            Dictionary with shift results
        """
        
        # Find cheapest N hours to charge
        shift_array = np.array(shift_hours)
        sorted_indices = np.argsort(shift_array)
        charge_hours_indices = sorted(sorted_indices[:self.cycle_hours].tolist())
        
        # Find most expensive N hours to discharge
        sorted_indices_desc = np.argsort(-shift_array)
        discharge_hours_indices = sorted(sorted_indices_desc[:self.cycle_hours].tolist())
        
        return {
            'shift_idx': shift_idx,
            'cycle_hours': self.cycle_hours,
            'charge_hours': charge_hours_indices,
            'discharge_hours': discharge_hours_indices,
            'prices_in_charge_hours': [float(shift_hours[i]) for i in charge_hours_indices],
            'prices_in_discharge_hours': [float(shift_hours[i]) for i in discharge_hours_indices],
            'avg_charge_price': float(np.mean([shift_hours[i] for i in charge_hours_indices])),
            'avg_discharge_price': float(np.mean([shift_hours[i] for i in discharge_hours_indices])),
        }
    
    def simulate_year(self):
        """
        Simulate full year with 12-hour shift strategy
        """
        
        results = {
            'metadata': {
                'battery_capacity_mwh': self.battery_capacity_mwh,
                'battery_power_mw': self.battery_power_mw,
                'cycle_hours': self.cycle_hours,
                'grid_tariff_uah_per_mwh': self.grid_tariff,
                'simulation_date': datetime.now().isoformat()
            },
            'daily_results': [],
            'total_summary': {
                'total_revenue_uah': 0,
                'total_cost_uah': 0,
                'net_profit_uah': 0,
                'total_charge_cycles': 0,
                'total_discharge_cycles': 0,
                'total_energy_battery_kwh': 0,
                'total_energy_grid_kwh': 0,
            }
        }
        
        soc_kwh = self.battery_capacity_kwh * 0.5  # Start at 50%
        
        for day_idx in range(365):
            start_hour = day_idx * 24
            end_hour = min(start_hour + 24, self.n_hours)
            
            if end_hour - start_hour < 24:
                break  # Incomplete day
            
            day_prices = self.prices[start_hour:end_hour]
            day_result = {
                'day': day_idx + 1,
                'shifts': [],
                'battery_revenue_uah': 0,
                'battery_cost_uah': 0,
                'grid_cost_uah': 0,
                'net_profit_uah': 0
            }
            
            # Process 2 shifts per day
            for shift_num in range(2):
                shift_start = shift_num * 12
                shift_end = shift_start + 12
                shift_hours = day_prices[shift_start:shift_end].tolist()
                
                # Optimize shift
                shift_plan = self.optimize_shift(shift_hours, shift_num)
                
                # Execute charge hours
                charge_energy_kwh = self.cycle_hours * self.battery_power_kw
                charge_cost = charge_energy_kwh * shift_plan['avg_charge_price'] / 1000
                
                # Add grid cost if battery not sufficient
                grid_charge_cost = 0
                if soc_kwh + charge_energy_kwh * np.sqrt(self.battery_rte) > self.battery_capacity_kwh:
                    # Battery would overflow - charge from grid instead
                    # Available grid power = unlimited (per Yaroslav's note)
                    pass
                else:
                    # Charge from grid
                    grid_charge_cost = charge_energy_kwh * (shift_plan['avg_charge_price'] + self.grid_tariff) / 1000
                    charge_cost = grid_charge_cost
                
                # Update SOC
                soc_kwh = min(self.battery_capacity_kwh, 
                            soc_kwh + charge_energy_kwh * np.sqrt(self.battery_rte))
                
                # Execute discharge hours
                discharge_energy_kwh = min(self.cycle_hours * self.battery_power_kw, soc_kwh)
                discharge_revenue = discharge_energy_kwh * shift_plan['avg_discharge_price'] / 1000
                
                # Update SOC
                soc_kwh = max(0, soc_kwh - discharge_energy_kwh)
                
                # Shift profit
                shift_profit = discharge_revenue - charge_cost
                
                shift_plan['charge_energy_kwh'] = charge_energy_kwh
                shift_plan['discharge_energy_kwh'] = discharge_energy_kwh
                shift_plan['charge_cost_uah'] = charge_cost
                shift_plan['discharge_revenue_uah'] = discharge_revenue
                shift_plan['shift_profit_uah'] = shift_profit
                shift_plan['soc_after_shift_kwh'] = float(soc_kwh)
                
                day_result['shifts'].append(shift_plan)
                day_result['battery_revenue_uah'] += discharge_revenue
                day_result['battery_cost_uah'] += charge_cost
                day_result['grid_cost_uah'] += grid_charge_cost
            
            day_result['net_profit_uah'] = day_result['battery_revenue_uah'] - day_result['battery_cost_uah']
            day_result['final_soc_kwh'] = float(soc_kwh)
            
            results['daily_results'].append(day_result)
            
            # Accumulate totals
            results['total_summary']['total_revenue_uah'] += day_result['battery_revenue_uah']
            results['total_summary']['total_cost_uah'] += day_result['battery_cost_uah']
            results['total_summary']['total_charge_cycles'] += 2
            results['total_summary']['total_discharge_cycles'] += 2
            results['total_summary']['total_energy_battery_kwh'] += sum(s['charge_energy_kwh'] for s in day_result['shifts'])
            results['total_summary']['total_energy_grid_kwh'] += day_result['grid_cost_uah']
            
            if (day_idx + 1) % 30 == 0:
                print(f"  Day {day_idx+1}/365 | Profit: {day_result['net_profit_uah']:>10,.0f} UAH | SOC: {soc_kwh:>6.0f} kWh")
        
        results['total_summary']['net_profit_uah'] = \
            results['total_summary']['total_revenue_uah'] - results['total_summary']['total_cost_uah']
        results['total_summary']['daily_avg_profit'] = \
            results['total_summary']['net_profit_uah'] / len(results['daily_results'])
        
        return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("="*100)
    print("🔋 V4-RDN-SHIFT: 12-Hour Shift Battery Trading with Price Arbitrage")
    print("="*100)
    
    try:
        # Load RDN prices
        with open('chervonohrad_data_corrected.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        rdn_prices = data['hourly_data']['price_rdn_uah_per_mwh']
        
        print(f"\n📊 RDN Price Data:")
        print(f"   Hours: {len(rdn_prices)}")
        print(f"   Min: {min(rdn_prices):.0f} UAH/MWh")
        print(f"   Max: {max(rdn_prices):.0f} UAH/MWh")
        print(f"   Avg: {np.mean(rdn_prices):.0f} UAH/MWh")
        
        # Create optimizer
        optimizer = V4RDNShift(
            rdn_prices_uah_per_mwh=rdn_prices,
            battery_capacity_mwh=10.0,
            battery_power_mw=2.5,
            battery_rte=0.88
        )
        
        # Simulate
        print(f"\n🔄 Simulating year with 12-hour shifts...")
        results = optimizer.simulate_year()
        
        # Summary
        summary = results['total_summary']
        print(f"\n" + "="*100)
        print(f"📈 ANNUAL RESULTS:")
        print(f"="*100)
        print(f"   Total Revenue:     {summary['total_revenue_uah']:>15,.0f} UAH")
        print(f"   Total Cost:        {summary['total_cost_uah']:>15,.0f} UAH")
        print(f"   Net Profit:        {summary['net_profit_uah']:>15,.0f} UAH")
        print(f"   Daily Avg Profit:  {summary['daily_avg_profit']:>15,.0f} UAH/day")
        print(f"\n   Charge Cycles:     {summary['total_charge_cycles']:>15.0f}")
        print(f"   Discharge Cycles:  {summary['total_discharge_cycles']:>15.0f}")
        print(f"   Total Energy (Battery): {summary['total_energy_battery_kwh']:>10,.0f} kWh")
        print(f"\n   Final SOC: {results['daily_results'][-1]['final_soc_kwh']:.0f} kWh (target: 50%)")
        print(f"="*100)
        
        # Save results
        import os
        os.makedirs('results', exist_ok=True)
        output_file = 'results/v4_rdn_shift_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to {output_file}")
        print(f"✅ V4-RDN-SHIFT simulation complete!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

