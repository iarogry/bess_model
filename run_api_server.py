#!/usr/bin/env python3
"""
Battery Simulator API Server
Главный запуск FastAPI сервера для управления энергетическими проектами
"""

import sys
import os
from pathlib import Path

# Добавить src в path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Запустить сервер
if __name__ == "__main__":
    import uvicorn
    
    # Конфигурация сервера
    config = {
        "app": "api.app:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": True,
        "log_level": "info",
        "access_log": True,
    }
    
    print("\n" + "="*80)
    print("🚀 BATTERY SIMULATOR API SERVER")
    print("="*80)
    print(f"📍 Host: {config['host']}")
    print(f"📍 Port: {config['port']}")
    print(f"📍 Reload: {config['reload']}")
    print(f"\n🌐 Open browser: http://localhost:{config['port']}/docs")
    print("="*80 + "\n")
    
    uvicorn.run(**config)
