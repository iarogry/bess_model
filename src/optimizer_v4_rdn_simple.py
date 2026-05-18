#!/usr/bin/env python3
"""
V4-RDN Simple - Pure RDN Trading Battery Optimizer
Simplified version focusing on price arbitrage (buy low, sell high)
"""

import numpy as np
import json
from datetime import datetime

class V4RDNSimple:
    """
    Simple RDN trading strategy: buy when price < avg, sell when price > avg
    This is a baseline to understand Yaroslav's optimization approach
    """
    
    def __init__(self,
                 rdn_prices_uah_per_mwh,
                 battery_capacity_mwh=10.0,
                 battery_power_mw=2.5,
                 battery_rte=0.88):
        """
        Args:
            rdn_prices_uah_per_mwh: array of hourly RDN prices [UAH/MWh]
            battery_capacity_mwh: battery capacity [MWh]
            battery_power_mw: max charge/discharge power [MW]
            battery_rte: round-trip efficiency [0-1]
        """
        
        self.prices = np.array(rdn_prices_uah_per_mwh, dtype=float)
        self.battery_capacity_kwh = battery_capacity_mwh * 1000
        self.battery_power_kw = battery_power_mw * 1000
        self.battery_rte = battery_rte
        
        self.n_hours = len(self.prices)
        
    def simple_strategy(self):
        """
        Simple threshold strategy: 
        - Buy (charge) when price < median
        - Sell (discharge) when price > median
        """
        
        median_price = np.median(self.prices)
        lower_quartile = np.percentile(self.prices, 25)
        upper_quartile = np.percentile(self.prices, 75)
        
        results = {
            'prices_stats': {
                'min': float(np.min(self.prices)),
                'max': float(np.max(self.prices)),
                'avg': float(np.mean(self.prices)),
                'median': float(median_price),
                'q25': float(lower_quartile),
                'q75': float(upper_quartile)
            },
            'hourly': []
        }
        
        soc_kwh = self.battery_capacity_kwh * 0.5  # Start at 50%
        total_revenue_uah = 0
        total_cost_uah = 0
        
        for h in range(self.n_hours):
            price = self.prices[h]
            hour_result = {
                'hour': h,
                'price_uah_per_mwh': float(price),
                'soc_start_kwh': float(soc_kwh),
                'action': 'idle',
                'energy_kwh': 0,
                'revenue_uah': 0
            }
            
            # Decision logic
            if price < lower_quartile and soc_kwh < self.battery_capacity_kwh * 0.9:
                # Buy (charge from grid)
                energy_kwh = min(self.battery_power_kw, 
                               self.battery_capacity_kwh * 0.9 - soc_kwh)
                cost = energy_kwh * price / 1000  # UAH
                
                soc_kwh += energy_kwh * np.sqrt(self.battery_rte)
                total_cost_uah += cost
                
                hour_result['action'] = 'charge'
                hour_result['energy_kwh'] = float(energy_kwh)
                hour_result['revenue_uah'] = float(-cost)
                
            elif price > upper_quartile and soc_kwh > self.battery_capacity_kwh * 0.1:
                # Sell (discharge to grid)
                energy_kwh = min(self.battery_power_kw, soc_kwh)
                revenue = energy_kwh * price / 1000  # UAH
                
                soc_kwh -= energy_kwh
                total_revenue_uah += revenue
                
                hour_result['action'] = 'discharge'
                hour_result['energy_kwh'] = float(energy_kwh)
                hour_result['revenue_uah'] = float(revenue)
            
            hour_result['soc_end_kwh'] = float(soc_kwh)
            results['hourly'].append(hour_result)
        
        results['summary'] = {
            'total_revenue_uah': float(total_revenue_uah),
            'total_cost_uah': float(total_cost_uah),
            'net_profit_uah': float(total_revenue_uah - total_cost_uah),
            'final_soc_kwh': float(soc_kwh),
            'n_charge_events': sum(1 for h in results['hourly'] if h['action'] == 'charge'),
            'n_discharge_events': sum(1 for h in results['hourly'] if h['action'] == 'discharge'),
            'total_energy_traded_kwh': sum(h['energy_kwh'] for h in results['hourly']),
        }
        
        return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("="*100)
    print("🔋 V4-RDN SIMPLE - Pure RDN Trading (Baseline Strategy)")
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
        optimizer = V4RDNSimple(
            rdn_prices_uah_per_mwh=rdn_prices,
            battery_capacity_mwh=10.0,
            battery_power_mw=2.5,
            battery_rte=0.88
        )
        
        # Run strategy
        print(f"\n🔄 Running simple RDN trading strategy...")
        results = optimizer.simple_strategy()
        
        print(f"\n📈 RESULTS:")
        print(f"   Total Revenue: {results['summary']['total_revenue_uah']:>15,.0f} UAH")
        print(f"   Total Cost:    {results['summary']['total_cost_uah']:>15,.0f} UAH")
        print(f"   Net Profit:    {results['summary']['net_profit_uah']:>15,.0f} UAH")
        print(f"   Daily Avg:     {results['summary']['net_profit_uah']/365:>15,.0f} UAH/day")
        print(f"\n   Charge Events:     {results['summary']['n_charge_events']}")
        print(f"   Discharge Events:  {results['summary']['n_discharge_events']}")
        print(f"   Total Energy:      {results['summary']['total_energy_traded_kwh']:,.0f} kWh")
        print(f"   Final SOC:         {results['summary']['final_soc_kwh']:.0f} kWh (50%)")
        
        # Save results
        output_file = 'results/v4_rdn_simple_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to {output_file}")
        
        print("\n" + "="*100)
        print("✅ V4-RDN Simple baseline complete")
        print("="*100)
        print(f"\n📌 This is a SIMPLE baseline using threshold strategy (buy low, sell high)")
        print(f"   Yaroslav's optimized model likely uses linear programming")
        print(f"   with day-to-day SOC rollover and potential lookahead optimization")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

