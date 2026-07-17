import logging
import yfinance as yf

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MarketWatcher:
    """
    Handles fetching and validating real-time gold spot (XAUUSD) prices.
    """
    
    @staticmethod
    def get_live_gold_price() -> float:
        """
        Fetches the current live spot price of Gold (GC=F / XAUUSD) from Yahoo Finance.
        Returns the last price as a float, or 0.0 if the fetch fails.
        """
        try:
            # 'GC=F' represents Gold COMEX Futures, which tracks spot prices almost identical to XAUUSD
            gold = yf.Ticker("GC=F")
            
            # Fetch current day's market data
            todays_data = gold.history(period="1d")
            
            if not todays_data.empty:
                # Get the most recent closing price
                last_price = todays_data['Close'].iloc[-1]
                logger.info(f"Successfully fetched live XAUUSD spot price: ${last_price:.2f}")
                return float(last_price)
            else:
                logger.warning("Market data retrieved was empty.")
                return 0.0
                
        except Exception as e:
            logger.error(f"Failed to fetch live gold price: {e}")
            return 0.0

    @classmethod
    def is_valid_entry(cls, proposed_entry: float, threshold_percent: float = 1.0) -> bool:
        """
        Verifies if an entered signal price is within a safe percentage of the live price.
        Helps catch massive typos (e.g. entering 240.00 instead of 2400.00).
        """
        live_price = cls.get_live_gold_price()
        if live_price == 0.0:
            # If the feed is down (or market is closed on weekends), bypass safety checks
            logger.warning("Bypassing price safety validation (market feed offline).")
            return True
            
        difference = abs(live_price - proposed_entry)
        max_allowed_diff = live_price * (threshold_percent / 100.0)
        
        return difference <= max_allowed_diff