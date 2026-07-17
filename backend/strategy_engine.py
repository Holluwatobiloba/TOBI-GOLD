import os
import sys
import time
import logging
import requests
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

# Ensure backend path resolves
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
API_SECRET_TOKEN = os.getenv("API_SECRET_TOKEN", "super_secure_system_token_2026")
API_URL = "http://127.0.0.1:8000/api/v1/signals"

class AlgoEngine:
    """
    Simulates an institutional automated trading desk.
    Analyzes historical data and generates technical signals.
    """

    @staticmethod
    def fetch_historical_data() -> pd.DataFrame:
        """
        Fetches the latest hourly market data for XAUUSD (GC=F).
        """
        try:
            gold = yf.Ticker("GC=F")
            # Pull past 5 days of hourly candles
            df = gold.history(period="5d", interval="1h")
            if df.empty:
                raise ValueError("No historical data returned from Yahoo Finance.")
            return df
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()

    @classmethod
    def run_ema_cross_strategy(cls):
        """
        Calculates EMA-9 and EMA-21 and checks for crossovers on the latest closed candle.
        """
        logger.info("Running Algorithmic EMA Strategy scan on XAUUSD...")
        df = cls.fetch_historical_data()
        if df.empty:
            return

        # Calculate Indicators
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()

        # We evaluate the second-to-last row [-2] because the latest candle [-1] is still actively forming
        last_closed_candle = df.iloc[-2]
        previous_closed_candle = df.iloc[-3]

        current_close = float(last_closed_candle['Close'])
        
        # Check for crossover
        was_bullish = previous_closed_candle['EMA_9'] > previous_closed_candle['EMA_21']
        is_bullish = last_closed_candle['EMA_9'] > last_closed_candle['EMA_21']

        direction = None
        notes = ""

        if not was_bullish and is_bullish:
            direction = "BUY"
            notes = "Algorithmic Bullish Crossover (EMA 9 crossed ABOVE EMA 21)"
        elif was_bullish and not is_bullish:
            direction = "SELL"
            notes = "Algorithmic Bearish Crossover (EMA 9 crossed BELOW EMA 21)"
        else:
            logger.info(f"Scan complete. No crossover detected. (EMA-9: {last_closed_candle['EMA_9']:.2f} | EMA-21: {last_closed_candle['EMA_21']:.2f})")
            # For testing purposes, if no crossover exists, we will simulate a market-aligned order:
            direction = "BUY" if is_bullish else "SELL"
            notes = f"Simulating active trend (EMA-9 is {'above' if is_bullish else 'below'} EMA-21)"

        if direction:
            # Set up safety targets relative to the current close price
            entry = round(current_close, 2)
            if direction == "BUY":
                sl = round(entry - 12.00, 2)  # 120 pip SL
                tp = round(entry + 24.00, 2)  # 240 pip TP (1:2 RR)
            else:
                sl = round(entry + 12.00, 2)
                tp = round(entry - 24.00, 2)

            # Fire off the webhook to our FastAPI server
            payload = {
                "direction": direction,
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "notes": notes
            }

            headers = {
                "Content-Type": "application/json",
                "X-Secure-Token": API_SECRET_TOKEN
            }

            try:
                logger.info(f"Dispatching auto-signal: {direction} entry near {entry}...")
                response = requests.post(API_URL, json=payload, headers=headers)
                if response.status_code == 202:
                    logger.info("Successfully dispatched automated strategy signal to webhook!")
                else:
                    logger.error(f"Webhook rejected signal: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Could not connect to FastAPI server: {e}")

if __name__ == "__main__":
    AlgoEngine.run_ema_cross_strategy()