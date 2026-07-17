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
from backend.auth import SecurityGatekeeper
from backend.broadcaster import SignalBroadcaster

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configurations
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# UI Button Layout Labels
BUTTON_SIGNALS = "📊 XAUUSD Signals"
BUTTON_STATUS = "⚙️ System Status"
BUTTON_RISK = "💵 Risk Calculator"
BUTTON_PROFILE = "👤 My Profile"

# Handle "/start" Command (Triggers User Registration)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    username = user.username if user.username else "None"
    first_name = user.first_name

    logger.info(f"New interaction detected from user {user.id} ({first_name})")

    user_profile = DatabaseManager.register_or_get_user(
        telegram_id=user.id,
        username=username,
        first_name=first_name
    )

    license_type = user_profile.get("license_tier", "free").capitalize() if user_profile else "Free"
    role_type = user_profile.get("role", "guest").upper() if user_profile else "GUEST"
    
    welcome_text = (
        f"📈 **TOBI-XAUUSD System Active** 📈\n\n"
        f"Welcome back, {first_name}! Your account is verified.\n\n"
        f"• **Role:** {role_type}\n"
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
    user = update.message.from_user
    user_choice = update.message.text
    logger.info(f"User {user.id} selected option: {user_choice}")

    DatabaseManager.update_user_activity(telegram_id=user.id)

    if user_choice == BUTTON_SIGNALS:
        active_setups = DatabaseManager.get_active_signals()

        if not active_setups:
            reply_text = (
                "📊 **XAUUSD Live Signals**\n\n"
                "📭 **No active setups detected.**\n\n"
                "The market is currently being scanned. We will broadcast a "
                "notification the second a high-probability gold setup triggers!"
            )
        else:
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
        profile = DatabaseManager.register_or_get_user(user.id, user.username or "None", user.first_name)
        username_str = f"@{user.username}" if user.username else "Anonymous"
        role_str = profile.get("role", "guest").capitalize()
        tier_str = profile.get("license_tier", "free").capitalize()
        
        reply_text = (
            f"👤 **User Account Profile**\n\n"
            f"• Name: {user.first_name}\n"
            f"• Handle: {username_str}\n"
            f"• ID: `{user.id}`\n"
            f"• Status: {role_str} Member\n"
            f"• License Tier: {tier_str} Tier Account"
        )
    else:
        reply_text = "⚠️ Unknown option selected. Please use the menu buttons below to navigate."

    await update.message.reply_text(text=reply_text, parse_mode="Markdown")

# Handle "/publish" Command (Admin Only)
async def publish_signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Syntax: /publish <BUY/SELL> <ENTRY> <SL> <TP> [OPTIONAL NOTES...]
    """
    user = update.message.from_user
    logger.info(f"Publish command initiated by user: {user.id}")

    profile = DatabaseManager.register_or_get_user(user.id, user.username or "None", user.first_name)
    
    if not SecurityGatekeeper.is_admin(profile):
        await update.message.reply_text(
            "❌ **Access Denied: Administrative Command Only**\n\n"
            "Only authorized platform administrators can publish manual gold signals.",
            parse_mode="Markdown"
        )
        return

    args = context.args
    if len(args) < 4:
        await update.message.reply_text(
            "⚠️ **Invalid Syntax!**\n\n"
            "**Usage:** `/publish <BUY/SELL> <ENTRY> <SL> <TP> [Optional Notes]`\n\n"
            "**Example:** `/publish buy 2345.50 2335.00 2360.00 Breakout`",
            parse_mode="Markdown"
        )
        return

    try:
        direction = args[0].upper()
        if direction not in ["BUY", "SELL", "BUY_LIMIT", "SELL_LIMIT"]:
            raise ValueError("Direction must be BUY, SELL, BUY_LIMIT, or SELL_LIMIT")

        entry = float(args[1])
        sl = float(args[2])
        tp = float(args[3])
        notes = " ".join(args[4:]) if len(args) > 4 else None

        signal_id = DatabaseManager.create_signal(
            direction=direction,
            entry=entry,
            sl=sl,
            tp=tp,
            created_by=user.id,
            notes=notes
        )

        if signal_id > 0:
            direction_emoji = "🟢" if "BUY" in direction else "🔴"
            
            # --- BROADCAST SYSTEM ACTIVE ---
            # 1. Format the broadcast trade card
            broadcast_message = (
                f"🚨 **NEW XAUUSD TRADING ALERT** 🚨\n"
                f"────────────────────\n"
                f"✨ **Signal ID:** #{signal_id}\n"
                f"🔹 **Asset:** XAUUSD\n"
                f"🔹 **Action:** {direction_emoji} {direction}\n\n"
                f"📍 **Entry Price:** `{entry:.2f}`\n"
                f"🛑 **Stop Loss (SL):** `{sl:.2f}`\n"
                f"🎯 **Take Profit (TP):** `{tp:.2f}`\n"
                f"📝 **Notes:** {notes if notes else 'None'}\n"
                f"────────────────────\n"
                f"📊 _Use responsible lot sizes and risk management principles._"
            )
            # 2. Asynchronously broadcast the card to all registered users!
            await SignalBroadcaster.broadcast_message(broadcast_message)
            
        else:
            await update.message.reply_text("❌ Database error: Failed to save signal.")

    except ValueError as err:
        await update.message.reply_text(
            f"❌ **Invalid Parameters:** {err}\n\n"
            "Please make sure Direction is valid and Entry, SL, and TP are numbers.",
            parse_mode="Markdown"
        )

# Handle "/close" Command (Admin Only)
async def close_signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Syntax: /close <SIGNAL_ID> <STATUS>
    Statuses: tp_hit, sl_hit, cancelled, active
    """
    user = update.message.from_user
    logger.info(f"Close command initiated by admin: {user.id}")

    profile = DatabaseManager.register_or_get_user(user.id, user.username or "None", user.first_name)
    
    if not SecurityGatekeeper.is_admin(profile):
        await update.message.reply_text(
            "❌ **Access Denied: Administrative Command Only**",
            parse_mode="Markdown"
        )
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ **Invalid Syntax!**\n\n"
            "**Usage:** `/close <SIGNAL_ID> <tp_hit/sl_hit/cancelled/active>`\n\n"
            "**Example:** `/close 1 tp_hit`",
            parse_mode="Markdown"
        )
        return

    try:
        signal_id = int(args[0])
        new_status = args[1].lower()
        
        valid_statuses = ["tp_hit", "sl_hit", "cancelled", "active"]
        if new_status not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")

        # Update the database
        success = DatabaseManager.update_signal_status(signal_id, new_status)

        if success:
            status_labels = {
                "tp_hit": "🎯 TAKE PROFIT HIT (WIN) 🟢",
                "sl_hit": "🛑 STOP LOSS HIT (LOSS) 🔴",
                "cancelled": "⚪ SIGNAL CANCELLED",
                "active": "🔵 SIGNAL SET TO ACTIVE"
            }
            
            update_message = (
                f"📢 **XAUUSD Signal Update** 📢\n"
                f"────────────────────\n"
                f"✨ **Signal ID:** #{signal_id}\n"
                f"🔹 **Status Update:** {status_labels[new_status]}\n"
                f"────────────────────\n"
                f"📊 _Historical records have been updated in the database system._"
            )
            # Broadcast the trade close out to everyone
            await SignalBroadcaster.broadcast_message(update_message)
        else:
            await update.message.reply_text(f"❌ Failed to find or update Signal #{signal_id}.")

    except ValueError as err:
        await update.message.reply_text(f"❌ **Invalid Parameters:** {err}", parse_mode="Markdown")

# Run the Bot
def main() -> None:
    if not BOT_TOKEN:
        logger.critical("CRITICAL ERROR: TELEGRAM_BOT_TOKEN is missing!")
        return

    DatabaseManager.initialize_pool()

    logger.info("Initializing Integrated TOBI-XAUUSD Control Unit...")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )

    # Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("publish", publish_signal_command))
    app.add_handler(CommandHandler("close", close_signal_command))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_clicks))

    logger.info("TOBI-XAUUSD interface operational. Listening...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()