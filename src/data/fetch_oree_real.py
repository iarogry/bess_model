"""
Fetch REAL RDN prices from OREE.com.ua
Replace the simulated prices with actual market data
"""

import sqlite3
import requests
from datetime import datetime, timedelta
from pathlib import Path
import logging
from bs4 import BeautifulSoup
import re
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data.db"


class OREERealFetcher:
    """Fetch actual RDN prices from OREE website"""
    
    # OREE endpoints
    DAM_URL = "https://www.oree.com.ua/index.php/control/results_mo/DAM"
    PRICES_PAGE = "https://www.oree.com.ua/index.php/pricectr?lang=english"
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_daily_prices(self, date_str: str) -> dict:
        """
        Fetch prices for a specific date from OREE
        
        Args:
            date_str: "2025-05-10" or "2026-05-09"
        
        Returns:
            {
                "date": "2025-05-10",
                "prices": [
                    {"hour": 1, "price": 2500},
                    ...
                ]
            }
        """
        
        try:
            # Try to get from DAM (Day-Ahead Market) page
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            # OREE format: DD.MM.YYYY
            date_formatted = date_obj.strftime("%d.%m.%Y")
            
            # Try direct API endpoint (if available)
            # https://www.oree.com.ua/index.php/control/results_mo/DAM?date=10.05.2025
            url = f"{self.DAM_URL}?date={date_formatted}"
            
            logger.info(f"Fetching {date_str} from {url}")
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} for {date_str}")
                return None
            
            # Parse HTML table
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find price table
            prices = self._parse_price_table(soup, date_str)
            
            if prices:
                return {
                    "date": date_str,
                    "prices": prices,
                    "source": "oree"
                }
            
            logger.warning(f"Could not parse prices for {date_str}")
            return None
        
        except Exception as e:
            logger.error(f"Error fetching {date_str}: {e}")
            return None
    
    def _parse_price_table(self, soup, date_str) -> list:
        """
        Parse OREE price table from HTML
        
        Table structure (typical):
        Hour | Price (грн/MWh) | ...
        1    | 2500             | ...
        2    | 2450             | ...
        ...
        """
        
        prices = []
        
        try:
            # Find all tables
            tables = soup.find_all('table')
            
            if not tables:
                logger.warning(f"No tables found for {date_str}")
                return []
            
            # Usually first table has prices
            for table in tables:
                rows = table.find_all('tr')
                
                if len(rows) < 25:  # Should have 24 hours + header
                    continue
                
                for i, row in enumerate(rows[1:], 1):  # Skip header
                    cols = row.find_all(['td', 'th'])
                    
                    if len(cols) < 2:
                        continue
                    
                    try:
                        # First column = hour
                        hour_text = cols[0].get_text().strip()
                        hour = int(re.sub(r'\D', '', hour_text))
                        
                        if hour < 1 or hour > 24:
                            continue
                        
                        # Second column = price
                        price_text = cols[1].get_text().strip()
                        price_text = re.sub(r'[^\d.,]', '', price_text)
                        price_text = price_text.replace(',', '.')
                        price = float(price_text)
                        
                        prices.append({
                            "hour": hour,
                            "price_hrn_per_mwh": price
                        })
                    
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Could not parse row {i}: {e}")
                        continue
                
                # If we found 24 prices, we're done
                if len(prices) == 24:
                    return sorted(prices, key=lambda x: x['hour'])
        
        except Exception as e:
            logger.error(f"Error parsing table: {e}")
        
        return prices
    
    def fetch_csv_export(self, date_str: str) -> dict:
        """
        Alternative: Download CSV from OREE export
        https://www.oree.com.ua/index.php/pricectr?lang=english
        Has "Download XLS" button
        """
        
        # This requires handling file download
        # Implement if OREE has CSV/XLS export
        logger.info(f"CSV export for {date_str} - not yet implemented")
        return None
    
    def load_historical_range_real(self, start_date: str, end_date: str, 
                                   rate_limit_sec: float = 2.0):
        """
        Load actual prices for date range from OREE
        
        Args:
            start_date: "2025-05-10"
            end_date: "2026-05-09"
            rate_limit_sec: Delay between requests (be polite!)
        """
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        current = start
        total_days = (end - start).days + 1
        loaded_count = 0
        failed_count = 0
        
        logger.info(f"Loading {total_days} days from OREE (polite rate: {rate_limit_sec}s)")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            
            # Fetch from OREE
            result = self.fetch_daily_prices(date_str)
            
            if result:
                # Store in DB
                try:
                    for price_data in result["prices"]:
                        cursor.execute("""
                            INSERT OR REPLACE INTO prices 
                            (date, hour, price_hrn_per_mwh, source)
                            VALUES (?, ?, ?, 'oree')
                        """, (date_str, price_data["hour"], price_data["price_hrn_per_mwh"]))
                    
                    conn.commit()
                    loaded_count += 1
                    logger.info(f"✅ {date_str} - {len(result['prices'])} prices")
                
                except Exception as e:
                    logger.error(f"Error storing {date_str}: {e}")
                    failed_count += 1
            else:
                failed_count += 1
                logger.warning(f"❌ {date_str} - fetch failed")
            
            # Be polite to OREE server
            time.sleep(rate_limit_sec)
            
            # Progress
            days_done = (current - start).days
            if days_done % 30 == 0:
                logger.info(f"Progress: {days_done}/{total_days} (loaded: {loaded_count}, failed: {failed_count})")
            
            current += timedelta(days=1)
        
        conn.close()
        
        logger.info(f"\nCompleted: {loaded_count}/{total_days} days loaded, {failed_count} failed")
        return loaded_count


def main():
    """Test: Fetch real prices for last 30 days"""
    
    fetcher = OREERealFetcher()
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    logger.info(f"Attempting to fetch real OREE prices: {start_date} to {end_date}")
    logger.info("(This might take a while due to rate limiting)")
    
    # Load real data
    loaded = fetcher.load_historical_range_real(start_date, end_date, rate_limit_sec=2.0)
    
    logger.info(f"\n✅ Loaded {loaded} days of real OREE prices")
    logger.info(f"Check database: {fetcher.db_path}")


if __name__ == "__main__":
    main()
