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
    version="1.0.0",
    description="Secure API to ingest automated market signals and broadcast alerts."
)

# Initialize database pool on startup
@app.on_event("startup")
def startup_event():
    DatabaseManager.initialize_pool()

# Pydantic Schema for Input Validation
class SignalPayload(BaseModel):
    direction: str = Field(..., description="BUY, SELL, BUY_LIMIT, or SELL_LIMIT")
    entry_price: float = Field(..., description="The trade entry execution price")
    stop_loss: float = Field(..., description="Stop Loss limit price")
    take_profit: float = Field(..., description="Take Profit target price")
    notes: str = Field(None, description="Optional strategy analysis or indicator details")

async def process_and_broadcast(payload: SignalPayload):
    """
    Background worker that saves the incoming signal and dispatches alerts.
    """
    direction_upper = payload.direction.upper()
    
    # Write the signal into PostgreSQL under a designated system user ID
    signal_id = DatabaseManager.create_signal(
        direction=direction_upper,
        entry=payload.entry_price,
        sl=payload.stop_loss,
        tp=payload.take_profit,
        created_by=9999,  # Reserved ID indicating automated system generation
        notes=payload.notes
    )

    if signal_id > 0:
        direction_emoji = "🟢" if "BUY" in direction_upper else "🔴"
        
        broadcast_message = (
            f"🚨 **AUTOMATED ALGORITHMIC ALERT** 🚨\n"
            f"────────────────────\n"
            f"✨ **Signal ID:** #{signal_id}\n"
            f"🔹 **Asset:** XAUUSD\n"
            f"🔹 **Action:** {direction_emoji} {direction_upper}\n\n"
            f"📍 **Entry Price:** `{payload.entry_price:.2f}`\n"
            f"🛑 **Stop Loss (SL):** `{payload.stop_loss:.2f}`\n"
            f"🎯 **Take Profit (TP):** `{payload.take_profit:.2f}`\n"
            f"📝 **Strategy:** {payload.notes if payload.notes else 'Algorithmic Breakout'}\n"
            f"────────────────────\n"
            f"🤖 _Dispatched automatically by the gold trading engine._"
        )
        # Global broadcast to all registered bot users
        await SignalBroadcaster.broadcast_message(broadcast_message)
    else:
        logger.error("Failed to write incoming API signal to database.")

@app.post("/api/v1/signals", status_code=status.HTTP_202_ACCEPTED)
async def ingest_signal(
    payload: SignalPayload,
    background_tasks: BackgroundTasks,
    x_secure_token: str = Header(..., alias="X-Secure-Token")
):
    """
    Receives trade updates from secure automated platforms.
    """
    # Verify the request contains the correct security token
    if x_secure_token != API_SECRET_TOKEN:
        logger.warning("Unauthorized webhook access attempt detected.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid security token."
        )

    logger.info(f"Accepted valid API signal: {payload.direction} @ {payload.entry_price}")
    
    # Hand off execution to background task to respond instantly to the sender
    background_tasks.add_task(process_and_broadcast, payload)
    
    return {"status": "accepted", "message": "Signal queued for processing."}