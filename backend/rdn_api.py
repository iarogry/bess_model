"""
Ukrainian RDN (Rhino Day-Ahead Market) API Integration
РДН - Ринок на день вперед (УКРЕНЕРГО)
"""

import aiohttp
import pandas as pd
from typing import List, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RDNClient:
    """
    Client for Ukrainian RDN prices
    
    Prices: UAH/MWh for each hour of the day (24/365)
    API: УКРЕНЕРГО Public API
    """
    
    BASE_URL = "https://api.ua-energy.org/open/api"  # Example endpoint
    
    def __init__(self):
        self.session = None
        self._cache = {}
    
    async def _ensure_session(self):
        """Create aiohttp session if needed"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def get_hourly_prices(self, date: datetime) -> List[float]:
        """
        Get 24 hourly RDN prices for a specific date
        
        Args:
            date: datetime object (only date matters)
        
        Returns:
            List of 24 floats: prices in UAH/MWh for hours 0-23
        """
        await self._ensure_session()
        
        cache_key = date.strftime("%Y-%m-%d")
        
        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Try to fetch from УКРЕНЕРГО API
            prices = await self._fetch_from_api(date)
            self._cache[cache_key] = prices
            return prices
        
        except Exception as e:
            logger.warning(f"Failed to fetch RDN prices for {cache_key}: {e}")
            # Fallback to synthetic data (realistic prices)
            return self._generate_synthetic_prices(date)
    
    async def _fetch_from_api(self, date: datetime) -> List[float]:
        """
        Fetch prices from УКРЕНЕРГО API
        
        Real implementation would use actual API endpoint
        """
        endpoint = f"{self.BASE_URL}/prices/rdn"
        params = {
            "date": date.strftime("%Y-%m-%d"),
            "currency": "UAH"
        }
        
        async with self.session.get(endpoint, params=params) as response:
            if response.status == 200:
                data = await response.json()
                # Parse response format: {hour: price_uah_per_mwh}
                prices = [data.get(f"hour_{i}", 2000) for i in range(24)]
                return prices
            else:
                raise Exception(f"API returned {response.status}")
    
    def _generate_synthetic_prices(self, date: datetime) -> List[float]:
        """
        Generate realistic synthetic RDN prices
        
        Typical Ukrainian market:
        - Night: 1500-2000 UAH/MWh (low demand)
        - Morning peak (6-9): 2500-3500 UAH/MWh
        - Midday: 2000-2500 UAH/MWh
        - Evening peak (18-21): 3000-4000 UAH/MWh
        - Late night: 1500-1800 UAH/MWh
        """
        prices = []
        base_price = 2200  # Base price UAH/MWh
        
        for hour in range(24):
            # Peak hours multiplier
            if 6 <= hour < 9:  # Morning peak
                multiplier = 1.5
            elif 18 <= hour < 21:  # Evening peak
                multiplier = 1.7
            elif hour < 6 or hour >= 21:  # Night
                multiplier = 0.75
            else:  # Midday
                multiplier = 1.1
            
            # Add some volatility based on date/hour
            volatility = (hash(str(date) + str(hour)) % 20 - 10) / 100
            price = base_price * multiplier * (1 + volatility)
            prices.append(max(1000, price))  # Minimum 1000 UAH/MWh
        
        return prices
    
    async def get_annual_prices(self, year: int) -> pd.DataFrame:
        """
        Get all 8760 hourly prices for a year
        
        Returns:
            DataFrame with columns: datetime, price_uah_per_mwh
        """
        start_date = datetime(year, 1, 1)
        prices_data = []
        
        for day_offset in range(365):
            date = start_date + timedelta(days=day_offset)
            daily_prices = await self.get_hourly_prices(date)
            
            for hour, price in enumerate(daily_prices):
                dt = date.replace(hour=hour)
                prices_data.append({
                    "datetime": dt,
                    "hour": hour,
                    "price_uah_per_mwh": price
                })
        
        return pd.DataFrame(prices_data)
    
    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()


# Mock prices for testing
MOCK_RDN_PRICES_2025 = {
    # Average prices by month (for quick testing)
    1: 2300,   # Jan
    2: 2200,   # Feb
    3: 2100,   # Mar
    4: 1900,   # Apr
    5: 1800,   # May
    6: 1700,   # Jun
    7: 1800,   # Jul
    8: 1900,   # Aug
    9: 2100,   # Sep
    10: 2300,  # Oct
    11: 2400,  # Nov
    12: 2500,  # Dec
}
