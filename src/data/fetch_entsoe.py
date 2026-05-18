"""
Fetch REAL prices from ENTSO-E Transparency Platform
https://transparency.entsoe.eu/

Ukraine codes:
  - 10YUA-WEPS-----0 (UA-BEI, main bidding zone)
  - 10Y1001C--000182 (UA-IPS, alternative)
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data.db"

try:
    from entsoe import Client
    import pandas as pd
    HAS_ENTSOE = True
except ImportError:
    HAS_ENTSOE = False
    logger.warning("entsoe-py not installed. Install with: pip install entsoe-py --break-system-packages")


class ENTSOEFetcher:
    """Fetch real prices from ENTSO-E Transparency Platform"""
    
    # Ukraine bidding zones (EIC codes)
    UA_BEI = "10YUA-WEPS-----0"      # Main bidding zone
    UA_IPS = "10Y1001C--000182"      # Alternative zone
    
    def __init__(self, security_token: str = None, db_path=DB_PATH):
        """
        Initialize ENTSO-E client
        
        Args:
            security_token: Get from https://transparency.entsoe.eu/
                           (requires free registration)
        """
        if not HAS_ENTSOE:
            logger.error("entsoe-py not installed")
            self.client = None
            return
        
        if not security_token:
            logger.warning("No security token provided")
            logger.info("Get token from: https://transparency.entsoe.eu/")
            self.client = None
        else:
            self.client = Client(security_token=security_token)
        
        self.db_path = db_path
    
    def fetch_daily_prices(self, date_str: str, bidding_zone=UA_BEI) -> dict:
        """
        Fetch day-ahead prices for Ukraine for a specific date
        
        Args:
            date_str: "2025-05-10"
            bidding_zone: "10YUA-WEPS-----0" (default) or "10Y1001C--000182"
        
        Returns:
            {
                "date": "2025-05-10",
                "prices": [
                    {"hour": 1, "price": 2500},
                    ...
                ]
            }
        """
        
        if not self.client:
            logger.error("ENTSO-E client not initialized")
            return None
        
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            # ENTSO-E API requires timezone-aware timestamps
            start = pd.Timestamp(date_obj, tz='UTC')
            end = start + timedelta(days=1)
            
            logger.info(f"Fetching prices for {date_str} from ENTSO-E...")
            
            # Query day-ahead prices
            prices_df = self.client.query_day_ahead_prices(
                country_code='UA',  # or bidding_zone directly
                start=start,
                end=end
            )
            
            if prices_df is None or prices_df.empty:
                logger.warning(f"No prices returned for {date_str}")
                return None
            
            # Parse results
            prices = []
            for idx, price in prices_df.items():
                # idx is the timestamp (hourly)
                hour = idx.hour + 1  # ENTSO-E uses 0-23, we use 1-24
                
                # Convert EUR/MWh to UAH/MWh (approx 1 EUR ≈ 40 UAH)
                price_uah = float(price) * 40  # Exchange rate approximation
                
                prices.append({
                    "hour": hour,
                    "price_hrn_per_mwh": price_uah
                })
            
            if prices:
                return {
                    "date": date_str,
                    "prices": sorted(prices, key=lambda x: x['hour']),
                    "source": "entsoe",
                    "currency_note": "EUR converted to UAH (1 EUR ≈ 40 UAH)"
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Error fetching {date_str}: {e}")
            return None
    
    def load_historical_range(self, start_date: str, end_date: str,
                             bidding_zone=UA_BEI):
        """
        Load prices for a date range from ENTSO-E
        
        Args:
            start_date: "2025-05-10"
            end_date: "2026-05-09"
        """
        
        if not self.client:
            logger.error("ENTSO-E client not configured")
            return 0
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        total_days = (end - start).days + 1
        loaded_count = 0
        failed_count = 0
        
        logger.info(f"Loading {total_days} days from ENTSO-E...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            
            result = self.fetch_daily_prices(date_str, bidding_zone)
            
            if result:
                try:
                    for price_data in result["prices"]:
                        cursor.execute("""
                            INSERT OR REPLACE INTO prices
                            (date, hour, price_hrn_per_mwh, source)
                            VALUES (?, ?, ?, 'entsoe')
                        """, (date_str, price_data["hour"], price_data["price_hrn_per_mwh"]))
                    
                    conn.commit()
                    loaded_count += 1
                    logger.info(f"✅ {date_str}")
                
                except Exception as e:
                    logger.error(f"Error storing {date_str}: {e}")
                    failed_count += 1
            else:
                failed_count += 1
            
            if (current - start).days % 30 == 0:
                logger.info(f"Progress: {(current - start).days}/{total_days} loaded")
            
            current += timedelta(days=1)
        
        conn.close()
        
        logger.info(f"\n✅ Loaded {loaded_count}/{total_days} days from ENTSO-E")
        return loaded_count


def main():
    """Example: Fetch last 30 days of real prices"""
    
    # You need to register and get token from:
    # https://transparency.entsoe.eu/
    TOKEN = None  # Put your token here
    
    if not TOKEN:
        logger.error("""
        ❌ Security token required!
        
        Steps to get token:
        1. Visit: https://transparency.entsoe.eu/
        2. Register (free account)
        3. Go to: https://transparency.entsoe.eu/usermgmt/User/ManageAPITokens
        4. Create API token
        5. Copy token and paste here
        
        Or pass via environment:
        export ENTSOE_TOKEN="your_token_here"
        python3 src/data/fetch_entsoe.py
        """)
        
        import os
        TOKEN = os.getenv('ENTSOE_TOKEN')
        
        if not TOKEN:
            logger.error("Token not found. Exiting.")
            return False
    
    # Fetch last 30 days
    fetcher = ENTSOEFetcher(security_token=TOKEN)
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    logger.info(f"Fetching: {start_date} to {end_date}")
    loaded = fetcher.load_historical_range(start_date, end_date)
    
    return loaded > 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
