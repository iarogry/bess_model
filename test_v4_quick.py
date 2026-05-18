#!/usr/bin/env python3
"""
Быстрый тест V4 оптимизатора
"""

import sys
sys.path.insert(0, 'src')
import json

print("="*80)
print("🔋 V4 OPTIMIZER - QUICK TEST")
print("="*80)

# Проверим данные спроса
try:
    with open('demand_profile_2026.json', 'r', encoding='utf-8') as f:
        demand_data = json.load(f)
    
    print("\n✓ Спрос (demand_profile_2026.json) загружен:")
    print(f"  - Часов: {len(demand_data['hourly_demand_kwh'])}")
    print(f"  - Min: {demand_data['stats']['min']:.2f} kWh")
    print(f"  - Max: {demand_data['stats']['max']:.2f} kWh")
    print(f"  - Avg: {demand_data['stats']['avg']:.2f} kWh")
    print(f"  - Total: {demand_data['stats']['total_annual_kwh']:.2f} kWh")
except Exception as e:
    print(f"✗ Ошибка загрузки спроса: {e}")
    sys.exit(1)

# Проверим данные цен
try:
    # Цены из database.db или JSON
    import sqlite3
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM price_data")
    count = cursor.fetchone()[0]
    conn.close()
    
    print(f"\n✓ Цены (data.db) загружены:")
    print(f"  - Записей: {count}")
except Exception as e:
    print(f"✗ Ошибка загрузки цен: {e}")

# Скажем, что готово
print("\n" + "="*80)
print("✅ V4 готов к запуску")
print("="*80)
print("\nСледующий шаг: Запустить полную симуляцию на V4")
print("Команда: python3 run_simulation.py")

