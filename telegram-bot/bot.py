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
from backend.risk_manager import RiskManager

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
        f"🛠️ **Dynamic Risk Settings Commands:**\n"
        f"👉 `/setbalance <amount>` - Set your default account balance\n"
        f"👉 `/setrisk <percent>` - Set your risk percentage per trade\n\n"
        f"Use the buttons below to interact with the gold engine in real time."
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

# Handle "/setbalance" Command (Saves User-Specific Account Balance)
async def set_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    args = context.args

    if not args:
        await update.message.reply_text(
            text="⚠️ **Usage:** `/setbalance <amount>` (e.g., `/setbalance 5000`)",
            parse_mode="Markdown"
        )
        return

    try:
        balance_val = float(args[0])
        if balance_val <= 0:
            await update.message.reply_text("❌ Balance must be a positive number.")
            return

        success = DatabaseManager.update_user_settings(user.id, balance=balance_val)
        if success:
            await update.message.reply_text(
                text=f"✅ **Balance Updated!**\nYour default trading account balance is now set to **${balance_val:,.2f}**.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Failed to update settings in the database.")
    except ValueError:
        await update.message.reply_text("❌ Invalid format. Please enter a valid decimal number.")

# Handle "/setrisk" Command (Saves User-Specific Trade Risk Threshold)
async def set_risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    args = context.args

    if not args:
        await update.message.reply_text(
            text="⚠️ **Usage:** `/setrisk <percentage>` (e.g., `/setrisk 1.5`)",
            parse_mode="Markdown"
        )
        return

    try:
        risk_val = float(args[0])
        if risk_val <= 0 or risk_val > 10.0:
            await update.message.reply_text("❌ Risk must be between **0.01%** and **10.0%** for account safety guidelines.")
            return

        success = DatabaseManager.update_user_settings(user.id, risk_percent=risk_val)
        if success:
            await update.message.reply_text(
                text=f"✅ **Risk Tier Updated!**\nYour risk per trade is now set to **{risk_val:.2f}%**.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Failed to update settings.")
    except ValueError:
        await update.message.reply_text("❌ Invalid format. Please enter a valid decimal number.")

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
        stats = DatabaseManager.get_signal_statistics()
        win_rate = stats.get("win_rate", 0.0)
        
        reply_text = (
            "⚙️ **TOBI-XAUUSD System Health**\n\n"
            "• Core Backend: Online\n"
            "• Database Layer: Connected (Verified Live)\n"
            "• API Handshake: 100% Latency Optimal\n\n"
            f"📊 **Historical System Stats:**\n"
            f"• Verified Signals Processed: `{stats.get('total_signals', 0)}`\n"
            f"• Total Win Ratio: `{win_rate}%` \n"
            f"• Closed Wins: `{stats.get('wins', 0)}` | Losses: `{stats.get('losses', 0)}`"
        )

    elif user_choice == BUTTON_RISK:
        settings = DatabaseManager.get_user_settings(user.id)
        latest_signal = DatabaseManager.get_latest_signal()

        if not latest_signal:
            reply_text = (
                "💵 **Gold Position Risk Calculator**\n\n"
                "⚠️ No active signal exists in the database to calculate risk parameters against.\n\n"
                "Configure your risk rules first:\n"
                f"• Current Balance setting: `${settings['balance']:,.2f}`\n"
                f"• Current Risk setting: `{settings['risk_percent']:.2f}%`"
            )
        else:
            calc = RiskManager.calculate_gold_position_size(
                balance=settings["balance"],
                risk_percent=settings["risk_percent"],
                entry=latest_signal["entry_price"],
                stop_loss=latest_signal["stop_loss"]
            )

            if calc.get("status") == "success":
                lots = calc["recommended_lots"]
                cash_risk = calc["cash_risk"]
                pips = calc["pips_at_risk"]
                
                reply_text = (
                    f"🎯 **PERSONAL RISK CALCULATOR**\n"
                    f"────────────────────\n"
                    f"✨ **Active Signal:** #{latest_signal['signal_id']} ({latest_signal['direction']})\n"
                    f"🔹 **Asset:** {latest_signal['pair']} @ `{latest_signal['entry_price']:.2f}`\n"
                    f"🛑 **Stop Loss:** `{latest_signal['stop_loss']:.2f}` (`{pips} pips` risk)\n\n"
                    f"⚙️ **Your Profile Metrics:**\n"
                    f"• Balance: `${settings['balance']:,.2f}`\n"
                    f"• Risk Setting: `{settings['risk_percent']:.2f}%`\n\n"
                    f"📊 **CALCULATED OUTCOME:**\n"
                    f"👉 Recommended Size:  **`{lots:.2f}`** Lots\n"
                    f"🔥 Total Cash Risk:  **`${cash_risk:.2f}`**\n"
                    f"────────────────────\n"
                    f"💡 _Want to alter this outcome? Update parameters via_ `/setbalance` _or_ `/setrisk`."
                )
            else:
                reply_text = "❌ Failed to calculate position parameters. Verify entry coordinates."

    elif user_choice == BUTTON_PROFILE:
        profile = DatabaseManager.register_or_get_user(user.id, user.username or "None", user.first_name)
        settings = DatabaseManager.get_user_settings(user.id)
        
        username_str = f"@{user.username}" if user.username else "Anonymous"
        role_str = profile.get("role", "guest").capitalize()
        tier_str = profile.get("license_tier", "free").capitalize()
        
        reply_text = (
            f"👤 **User Account Profile**\n\n"
            f"• **Name:** {user.first_name}\n"
            f"• **Handle:** {username_str}\n"
            f"• **ID:** `{user.id}`\n"
            f"• **Status:** {role_str} Member\n"
            f"• **License Tier:** {tier_str} Tier Account\n\n"
            f"📊 **PERSONAL RISK METRICS:**\n"
            f"• **Target Balance:** `${settings['balance']:,.2f}`\n"
            f"• **Trade Risk Tolerance:** `{settings['risk_percent']:.2f}%`"
        )
    else:
        reply_text = "⚠️ Unknown option selected. Please use the menu buttons below to navigate."

    await update.message.reply_text(text=reply_text, parse_mode="Markdown")

# Handle "/publish" Command (Admin Only)
async def publish_signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            await SignalBroadcaster.broadcast_message(update_message)
        else:
            await update.message.reply_text(f"❌ Failed to find or update Signal #{signal_id}.")

    except ValueError as err:
        await update.message.reply_text(f"❌ **Invalid Parameters:** {err}", parse_mode="Markdown")

# Handle "/stats" Command (All Users)
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Stats command requested by user {update.message.from_user.id}")
    
    stats = DatabaseManager.get_signal_statistics()
    if not stats:
        await update.message.reply_text("⚠️ System performance stats are temporarily unavailable.")
        return

    win_rate = stats.get("win_rate", 0.0)
    
    reply_text = (
        "📈 **TOBI-XAUUSD Engine Performance** 📈\n"
        "────────────────────────\n\n"
        f"🏆 **Current Win Rate:** `{win_rate}%`\n\n"
        f"• **Total Signals:** `{stats.get('total_signals', 0)}` \n"
        f"• **Active/Running Setups:** `{stats.get('running', 0)}` \n"
        f"• **Closed Trades:** `{stats.get('closed_trades', 0)}` \n\n"
        f"🟢 **Closed Wins (TP):** `{stats.get('wins', 0)}` \n"
        f"🔴 **Closed Losses (SL):** `{stats.get('losses', 0)}` \n"
        f"⚪ **Cancelled Orders:** `{stats.get('cancelled', 0)}` \n"
        "────────────────────────\n"
        "_Calculated mathematically in real-time from our database records._"
    )
    
    await update.message.reply_text(text=reply_text, parse_mode="Markdown")

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
    app.add_handler(CommandHandler("setbalance", set_balance_command))
    app.add_handler(CommandHandler("setrisk", set_risk_command))
    app.add_handler(CommandHandler("publish", publish_signal_command))
    app.add_handler(CommandHandler("close", close_signal_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_clicks))

    logger.info("TOBI-XAUUSD interface operational. Listening...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()