
OPTIMIZER V4-SCIPY-FIXED: Correct Energy Conservation

VARIABLES (per hour, 24 hours total):
  - pv_to_demand[h]:      PV used for demand (0 to pv_available[h])
  - pv_to_export[h]:      PV exported directly (0 to pv_available[h])
  - batt_charge[h]:       Battery charging (0 to 500 kW)
  - batt_discharge[h]:    Battery discharge (0 to 500 kW)
  - grid_import[h]:       Grid import (0 to 5000 kW)
  - grid_export[h]:       Grid export (0 to 5000 kW)
  - soc[h]:               Battery state of charge (1000 to 4000 kWh)

CONSTRAINTS (per hour):
  1. PV CONSERVATION: pv_to_demand + pv_to_export + pv_to_charge <= pv_available[h]
     (where pv_to_charge is the PV that goes to battery, not explicit variable)
  
  2. ENERGY BALANCE FOR DEMAND: 
     pv_to_demand + batt_discharge*0.8 + grid_import >= demand[h]
  
  3. ENERGY BALANCE FOR EXPORT:
     pv_to_export + excess_batt_discharge <= pv_available[h] (no free energy!)
     (export can only come from PV or battery)
  
  4. BATTERY SOC:
     soc[h] = soc[h-1] - batt_discharge*1.2 + batt_charge
     (batt_discharge*1.2 accounts for 20% loss)
  
  5. SOC BOUNDS:
     1000 <= soc[h] <= 4000

OBJECTIVE:
  Maximize: Σ[grid_export[h] * price[h]] - Σ[grid_import[h] * (price[h] + tariffs)] - Σ[battery_losses]

This formulation properly conserves energy at each hour.
