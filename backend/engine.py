import os
import time
import asyncio
import logging
import pandas as pd
import yfinance as yf
from datetime import datetime
from backend.database import DatabaseManager
from backend.broadcaster import SignalBroadcaster
from backend.executor import MetaTraderExecutor

# Setup logger to align with system standards
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class StrategyEngine:
    def __init__(self):
        self.symbol = "GC=F"  # Gold Futures ticker used for spot market proxy
        self.broadcaster = SignalBroadcaster()
        self.executor = MetaTraderExecutor()  # Automated execution bridge to MT5
        
    def fetch_market_data(self):
        """Fetches latest M15 data matrix for Gold from Yahoo Finance"""
        gold = yf.Ticker(self.symbol)
        df = gold.history(period="5d", interval="15m")
        return df

    def calculate_indicators(self, df):
        """Computes Technical Indicators (EMA, RSI, ATR)"""
        # EMAs
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        # RSI 14
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        # ATR 14 (Average True Range)
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR_14'] = true_range.rolling(14).mean()
        
        return df

    async def scan_and_execute(self):
        """Runs the quantitative engine against live data using the 80/20 framework"""
        logger.info("Executing automated 'Best Mode' 80/20 XAUUSD strategy scan...")
        
        try:
            df = self.fetch_market_data()
            if df.empty or len(df) < 30:
                logger.warning("Insufficient market data collected from ticker.")
                return
                
            df = self.calculate_indicators(df)
            
            # Extract last two completed candle bars to detect true crossover
            prev_row = df.iloc[-3]
            current_row = df.iloc[-2]
            
            close_price = float(current_row['Close'])
            atr = float(current_row['ATR_14'])
            rsi = float(current_row['RSI_14'])
            
            # Detect Moving Average Crosses
            bullish_cross = (prev_row['EMA_9'] <= prev_row['EMA_21']) and (current_row['EMA_9'] > current_row['EMA_21'])
            bearish_cross = (prev_row['EMA_9'] >= prev_row['EMA_21']) and (current_row['EMA_9'] < current_row['EMA_21'])
            
            signal_type = None
            sl = 0.0
            tp = 0.0

            # --- OPTIMIZED 80/20 MOMENTUM RULE SET ---
            if bullish_cross and rsi < 80:
                signal_type = "BUY"
                sl = close_price - (1.5 * atr)
                tp = close_price + (3.0 * atr)
                
            elif bearish_cross and rsi > 20:
                signal_type = "SELL"
                sl = close_price + (1.5 * atr)
                tp = close_price - (3.0 * atr)

            if signal_type:
                logger.info(f"🔥 ALGO PATTERN DETECTED: {signal_type} @ {close_price:.2f}")
                
                # 1. Save Signal directly into PostgreSQL container using DatabaseManager
                signal_id = DatabaseManager.create_signal(
                    direction=signal_type,
                    entry=close_price,
                    sl=sl,
                    tp=tp,
                    created_by=9999,
                    notes=f"Engine 80/20 strategy scan. RSI: {rsi:.1f} | ATR: {atr:.2f}"
                )
                
                if signal_id > 0:
                    # 2. ⚡ LIVE AUTOMATIC EXECUTION VIA MT5 BRIDGE ⚡
                    # Sends trade order into containerized MT5 demo terminal (using a safe starter lot size: 0.02)
                    auto_trade_success = self.executor.execute_market_order(
                        symbol="GC=F",
                        order_type=signal_type,
                        volume=0.02,
                        price=close_price,
                        sl=sl,
                        tp=tp
                    )
                    
                    # 3. Construct and dispatch Telegram notification alert
                    direction_emoji = "🟢" if signal_type == "BUY" else "🔴"
                    status_note = "✅ EXECUTED ON DEMO" if auto_trade_success else "❌ BROKER ORDER REJECTED"
                    
                    broadcast_msg = (
                        f"🚨 **AUTONOMOUS TRADING ALERT** 🚨\n"
                        f"────────────────────\n"
                        f"✨ **Signal ID:** #{signal_id}\n"
                        f"🔹 **Action:** {direction_emoji} {signal_type}\n"
                        f"📊 **Execution Status:** `{status_note}`\n\n"
                        f"📍 **Entry Price:** `{close_price:.2f}`\n"
                        f"🛑 **Stop Loss (SL):** `{sl:.2f}`\n"
                        f"🎯 **Take Profit (TP):** `{tp:.2f}`\n"
                        f"📝 **Strategy Parameters:** RSI {rsi:.1f} | ATR {atr:.2f}\n"
                        f"────────────────────\n"
                        f"🤖 _Managed, recorded, and executed completely by server pipeline._"
                    )
                    await SignalBroadcaster.broadcast_message(broadcast_msg)
            else:
                logger.info("Scan complete. No 80/20 crossover signals triggered.")
                
        except Exception as e:
            logger.error(f"Error executing strategy runtime loop: {e}")

    async def start_engine_loop(self):
        """Asynchronous execution scheduler set for 15-minute checking loops"""
        while True:
            await self.scan_and_execute()
            # Sleep for 15 minutes (900 seconds)
            await asyncio.sleep(900)

if __name__ == "__main__":
    engine = StrategyEngine()
    asyncio.run(engine.start_engine_loop())