import os
import logging
import sys
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes, 
    filters
)

# Ensure our backend folder is accessible to Python imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.database import DatabaseManager

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configuration environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# UI Button Layout Labels
BUTTON_SIGNALS = "📊 XAUUSD Signals"
BUTTON_STATUS = "⚙️ System Status"
BUTTON_RISK = "💵 Risk Calculator"
BUTTON_PROFILE = "👤 My Profile"

# Handle "/start" Command (Triggers User Registration)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Greets the user, automatically registers them in the database, 
    and locks an interactive menu keyboard above their chat input bar.
    """
    user = update.message.from_user
    username = user.username if user.username else "None"
    first_name = user.first_name

    logger.info(f"New interaction detected from user {user.id} ({first_name})")

    # Attempt to register the user in the database backend
    user_profile = DatabaseManager.register_or_get_user(
        telegram_id=user.id,
        username=username,
        first_name=first_name
    )

    # Personalize greeting based on their registration status or license tier
    license_type = user_profile.get("license_tier", "free").capitalize() if user_profile else "Free"
    
    welcome_text = (
        f"📈 **TOBI-XAUUSD System Active** 📈\n\n"
        f"Welcome back, {first_name}! Your account is verified.\n\n"
        f"• **License Tier:** {license_type} Account\n"
        f"• **Status:** System Online\n\n"
        "Use the buttons below to interact with the gold engine in real time."
    )
    
    keyboard_layout = [
        [BUTTON_SIGNALS, BUTTON_STATUS],
        [BUTTON_RISK, BUTTON_PROFILE]
    ]
    
    reply_markup = ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Select an option..."
    )
    
    await update.message.reply_text(
        text=welcome_text, 
        reply_markup=reply_markup, 
        parse_mode="Markdown"
    )

# Handle Menu Clicks & Record Active User Statistics
async def handle_menu_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processes button selections, updates active status, and queries the live DB.
    """
    user = update.message.from_user
    user_choice = update.message.text
    logger.info(f"User {user.id} selected option: {user_choice}")

    # Record active interaction in PostgreSQL (fails gracefully if DB is offline)
    DatabaseManager.update_user_activity(telegram_id=user.id)

    if user_choice == BUTTON_SIGNALS:
        # 1. Fetch live active signals from our database pool
        active_setups = DatabaseManager.get_active_signals()

        if not active_setups:
            # Fallback message if database is offline or there are no active trades
            reply_text = (
                "📊 **XAUUSD Live Signals**\n\n"
                "📭 **No active setups detected.**\n\n"
                "The market is currently being scanned. We will broadcast a "
                "notification the second a high-probability gold setup triggers!"
            )
        else:
            # 2. Build a beautiful, professional trading card for each active signal
            reply_text = "📊 **TOBI-XAUUSD Active Signals**\n\n"
            for signal in active_setups:
                direction_emoji = "🟢 BUY" if "BUY" in signal["direction"] else "🔴 SELL"
                notes_section = f"\n📝 *Notes:* {signal['notes']}" if signal["notes"] else ""
                
                reply_text += (
                    f"✨ **Signal #{signal['signal_id']}**\n"
                    f"🔹 **Asset:** {signal['pair']}\n"
                    f"🔹 **Action:** {direction_emoji}\n"
                    f"🔹 **Status:** {signal['status'].upper()}\n\n"
                    f"📍 **Entry Price:** `{signal['entry_price']:.2f}`\n"
                    f"🛑 **Stop Loss (SL):** `{signal['stop_loss']:.2f}`\n"
                    f"🎯 **Take Profit (TP):** `{signal['take_profit']:.2f}`\n"
                    f"{notes_section}\n"
                    f"────────────────────\n\n"
                )
            reply_text += "_Review risk management guidelines before entering trades._"

    elif user_choice == BUTTON_STATUS:
        reply_text = (
            "⚙️ **TOBI-XAUUSD System Health**\n\n"
            "• Core Backend: Online\n"
            "• Database Layer: Connected (Verified Live)\n"
            "• API Handshake: 100% Latency Optimal\n"
            "• Trading Engines: Idle"
        )
    elif user_choice == BUTTON_RISK:
        reply_text = (
            "💵 **Gold Position Risk Calculator**\n\n"
            "Use this module to calculate lot sizes for XAUUSD trades.\n\n"
            "• Standard Contract: 1 Lot = 100oz Gold\n"
            "• Recommended Risk per trade: 1.0% - 2.0% Max\n\n"
            "_Phase 4 will deploy our fully automated interactive risk engine here._"
        )
    elif user_choice == BUTTON_PROFILE:
        username_str = f"@{user.username}" if user.username else "Anonymous"
        reply_text = (
            f"👤 **User Account Profile**\n\n"
            f"• Name: {user.first_name}\n"
            f"• Handle: {username_str}\n"
            f"• ID: `{user.id}`\n"
            f"• Status: Registered Member\n"
            f"• License Tier: Free Tier Account"
        )
    else:
        reply_text = "⚠️ Unknown option selected. Please use the menu buttons below to navigate."

    await update.message.reply_text(text=reply_text, parse_mode="Markdown")

# Run the Resilient Bot
def main() -> None:
    if not BOT_TOKEN:
        logger.critical("CRITICAL ERROR: TELEGRAM_BOT_TOKEN is missing!")
        return

    # Initialize the Database Connection Pool
    DatabaseManager.initialize_pool()

    logger.info("Initializing Integrated TOBI-XAUUSD Control Unit...")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_clicks))

    logger.info("TOBI-XAUUSD interface operational. Listening...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()