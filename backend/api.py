import os
import sys
import logging
from fastapi import FastAPI, Header, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Robust path injection to ensure backend modules resolve correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.database import DatabaseManager
from backend.broadcaster import SignalBroadcaster
from backend.market_watcher import MarketWatcher
from backend.risk_manager import RiskManager  # NEW: Integrated Risk Manager

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
API_SECRET_TOKEN = os.getenv("API_SECRET_TOKEN", "super_secure_system_token_2026")

app = FastAPI(
    title="TOBI-XAUUSD Webhook Ingestor",
    version="1.2.0",
    description="Secure API to ingest validated market signals with dynamic risk calculations."
)

# Initialize database pool on startup
@app.on_event("startup")
def startup_event():
    DatabaseManager.initialize_pool()

class SignalPayload(BaseModel):
    direction: str = Field(..., description="BUY, SELL, BUY_LIMIT, or SELL_LIMIT")
    entry_price: float = Field(..., description="The trade entry execution price")
    stop_loss: float = Field(..., description="Stop Loss limit price")
    take_profit: float = Field(..., description="Take Profit target price")
    notes: str = Field(None, description="Optional strategy analysis or details")

async def process_and_broadcast(payload: SignalPayload):
    direction_upper = payload.direction.upper()
    
    # Save to DB under system bot ID
    signal_id = DatabaseManager.create_signal(
        direction=direction_upper,
        entry=payload.entry_price,
        sl=payload.stop_loss,
        tp=payload.take_profit,
        created_by=9999,
        notes=payload.notes
    )

    if signal_id > 0:
        direction_emoji = "🟢" if "BUY" in direction_upper else "🔴"
        
        # --- NEW: DYNAMIC RISK CALCULATIONS ---
        # Compute lot sizes for standard account tiers at 1% risk
        risk_1k = RiskManager.calculate_gold_position_size(1000, 1.0, payload.entry_price, payload.stop_loss)
        risk_5k = RiskManager.calculate_gold_position_size(5000, 1.0, payload.entry_price, payload.stop_loss)
        risk_10k = RiskManager.calculate_gold_position_size(10000, 1.0, payload.entry_price, payload.stop_loss)
        
        # Safely extract recommended lots or default to a safe minimum
        lots_1k = risk_1k.get("recommended_lots", 0.01) if risk_1k.get("status") == "success" else 0.01
        lots_5k = risk_5k.get("recommended_lots", 0.05) if risk_5k.get("status") == "success" else 0.05
        lots_10k = risk_10k.get("recommended_lots", 0.10) if risk_10k.get("status") == "success" else 0.10
        pips_risk = risk_1k.get("pips_at_risk", 0)

        broadcast_message = (
            f"🚨 **AUTOMATED ALGORITHMIC ALERT** 🚨\n"
            f"────────────────────\n"
            f"✨ **Signal ID:** #{signal_id}\n"
            f"🔹 **Asset:** XAUUSD\n"
            f"🔹 **Action:** {direction_emoji} {direction_upper}\n\n"
            f"📍 **Entry Price:** `{payload.entry_price:.2f}`\n"
            f"🛑 **Stop Loss (SL):** `{payload.stop_loss:.2f}` (`{pips_risk} pips` risk)\n"
            f"🎯 **Take Profit (TP):** `{payload.take_profit:.2f}`\n"
            f"📝 **Strategy:** {payload.notes if payload.notes else 'Algorithmic Breakout'}\n"
            f"────────────────────\n"
            f"📊 **DYNAMIC RISK GUIDANCE (1% Risk):**\n"
            f"• `$1,000 Account` ➔  **`{lots_1k:.2f}`** Lots\n"
            f"• `$5,000 Account` ➔  **`{lots_5k:.2f}`** Lots\n"
            f"• `$10,000 Account` ➔  **`{lots_10k:.2f}`** Lots\n"
            f"────────────────────\n"
            f"🤖 _Verified safe against live feed & dispatched by engine._"
        )
        await SignalBroadcaster.broadcast_message(broadcast_message)
    else:
        logger.error("Failed to write incoming API signal to database.")

@app.post("/api/v1/signals", status_code=status.HTTP_202_ACCEPTED)
async def ingest_signal(
    payload: SignalPayload,
    background_tasks: BackgroundTasks,
    x_secure_token: str = Header(..., alias="X-Secure-Token")
):
    if x_secure_token != API_SECRET_TOKEN:
        logger.warning("Unauthorized webhook access attempt detected.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid security token."
        )

    # Validate proposed entry price is within 1.5% of live gold market spot
    if not MarketWatcher.is_valid_entry(payload.entry_price, threshold_percent=1.5):
        live_spot = MarketWatcher.get_live_gold_price()
        logger.warning(
            f"Blocked anomalous signal: Entry {payload.entry_price} "
            f"deviates significantly from live spot ${live_spot:.2f}"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Signal entry price deviates too far from live market spot (${live_spot:.2f})."
        )

    logger.info(f"Accepted valid API signal: {payload.direction} @ {payload.entry_price}")
    background_tasks.add_task(process_and_broadcast, payload)
    
    return {"status": "accepted", "message": "Signal verified and queued."}