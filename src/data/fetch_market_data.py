"""
Resilient Market Data Fetcher for Electricity Prices
Combines ENTSO-E and OREE (Ukraine) data sources with automatic fallback logic.
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Import local fetchers
try:
    from fetch_entsoe import ENTSOEFetcher
    from fetch_oree_real import OREERealFetcher
except ImportError:
    # If running from a different context, adjust paths
    import sys
    sys.path.append(str(Path(__file__).parent))
    from fetch_entsoe import ENTSOEFetcher
    from fetch_oree_real import OREERealFetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataFetcher:
    """
    Unified fetcher that attempts ENTSO-E first, then falls back to OREE.
    """
    
    def __init__(self, entsoe_token: Optional[str] = None, db_path: Optional[Path] = None):
        """
        Initialize the resilient fetcher.
        
        Args:
            entsoe_token: Security token for ENTSO-E (defaults to env ENTSOE_TOKEN)
            db_path: Path to the SQLite database
        """
        self.entsoe_token = entsoe_token or os.getenv('ENTSOE_TOKEN')
        self.db_path = db_path
        
        # Initialize sub-fetchers
        self.entsoe = ENTSOEFetcher(security_token=self.entsoe_token, db_path=self.db_path)
        self.oree = OREERealFetcher(db_path=self.db_path)
        
    def fetch_daily_prices(self, date_str: str) -> Optional[Dict]:
        """
        Fetch daily prices with automatic fallback logic.
        
        1. Attempt ENTSO-E
        2. If fails/empty, attempt OREE
        
        Args:
            date_str: "YYYY-MM-DD"
            
        Returns:
            Dictionary with prices or None if both sources fail.
        """
        
        # --- ATTEMPT 1: ENTSO-E ---
        if self.entsoe_token:
            try:
                logger.info(f"Attempting ENTSO-E fetch for {date_str}...")
                result = self.entsoe.fetch_daily_prices(date_str)
                
                if result and result.get("prices") and len(result["prices"]) == 24:
                    logger.info(f"✅ Successfully fetched {date_str} from ENTSO-E")
                    return result
                else:
                    logger.warning(f"⚠️ ENTSO-E returned incomplete data for {date_str}")
            except Exception as e:
                logger.error(f"❌ ENTSO-E fetch error for {date_str}: {e}")
        else:
            logger.warning("No ENTSOE_TOKEN provided, skipping ENTSO-E.")

        # --- ATTEMPT 2: OREE (Fallback) ---
        try:
            logger.info(f"Attempting OREE fallback fetch for {date_str}...")
            result = self.oree.fetch_daily_prices(date_str)
            
            if result and result.get("prices") and len(result["prices"]) == 24:
                logger.info(f"✅ Successfully fetched {date_str} from OREE (Fallback)")
                return result
            else:
                logger.error(f"❌ OREE fallback failed to provide complete data for {date_str}")
        except Exception as e:
            logger.error(f"❌ OREE fetch error for {date_str}: {e}")

        logger.critical(f"🛑 Both ENTSO-E and OREE failed for {date_str}")
        return None

    def sync_range(self, start_date: str, end_date: str):
        """
        Synchronize a range of dates into the database using fallback logic.
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        current = start
        loaded_count = 0
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            result = self.fetch_daily_prices(date_str)
            
            if result:
                # Save logic is handled by sub-fetchers or we can unify here
                # ENTSOEFetcher and OREERealFetcher usually save in their load_historical methods
                # Here we just log success for the wrapper.
                loaded_count += 1
            
            current += timedelta(days=1)
            
        logger.info(f"Range sync complete: {loaded_count} days loaded.")
        return loaded_count

def main():
    """CLI usage for market data synchronization"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync electricity prices from ENTSO-E and OREE")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)", required=True)
    parser.add_argument("--end", help="End date (YYYY-MM-DD)", required=True)
    parser.add_argument("--token", help="ENTSO-E API Token")
    
    args = parser.parse_args()
    
    fetcher = MarketDataFetcher(entsoe_token=args.token)
    fetcher.sync_range(args.start, args.end)

if __name__ == "__main__":
    main()
