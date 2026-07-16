import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes, 
    filters
)

# 1. Setup system-wide logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Define the custom menu button labels
BUTTON_SIGNALS = "📊 XAUUSD Signals"
BUTTON_STATUS = "⚙️ System Status"
BUTTON_RISK = "💵 Risk Calculator"
BUTTON_PROFILE = "👤 My Profile"

# 3. Handle "/start" command (displays our custom interactive menu)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Greets the user and locks an interactive button keyboard above their chat bar.
    """
    welcome_text = (
        "📈 **TOBI-XAUUSD System Active** 📈\n\n"
        "Welcome to your professional gold trading command center.\n\n"
        "Use the buttons below to interact with the system in real time."
    )
    
    # Grid layout for our menu: Row 1 has two buttons, Row 2 has two buttons
    keyboard_layout = [
        [BUTTON_SIGNALS, BUTTON_STATUS],
        [BUTTON_RISK, BUTTON_PROFILE]
    ]
    
    # Build the custom keyboard markup
    reply_markup = ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,         # Auto-resizes the buttons to fit mobile screens
        is_persistent=True,           # Keeps the menu locked open so it doesn't vanish
        input_field_placeholder="Select an option..." # Help text in the chat input bar
    )
    
    await update.message.reply_text(
        text=welcome_text, 
        reply_markup=reply_markup, 
        parse_mode="Markdown"
    )

# 4. Handle menu selection clicks
async def handle_menu_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Listens to button taps and sends back dedicated replies for each option.
    """
    user_choice = update.message.text
    logger.info(f"User selected: {user_choice}")

    if user_choice == BUTTON_SIGNALS:
        reply_text = (
            "📊 **XAUUSD Signals Panel**\n\n"
            "Currently tracking gold volatility sessions...\n"
            "• Active Signals: None\n"
            "• Next Session: London Liquidity Open\n\n"
            "_Phase 2 will integrate live automation signals here._"
        )
    elif user_choice == BUTTON_STATUS:
        reply_text = (
            "⚙️ **TOBI-XAUUSD System Health**\n\n"
            "• Core Backend: Online\n"
            "• Database Layer: Not Connected (Phase 1 Setup pending)\n"
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
        user = update.message.from_user
        username = f"@{user.username}" if user.username else "Anonymous"
        reply_text = (
            f"👤 **User Account Profile**\n\n"
            f"• Name: {user.first_name}\n"
            f"• Handle: {username}\n"
            f"• Status: Registered Guest\n"
            f"• License Tier: Free Tier Account"
        )
    else:
        # Fallback response if user types something random
        reply_text = "⚠️ Unknown option selected. Please use the menu buttons below to navigate."

    await update.message.reply_text(text=reply_text, parse_mode="Markdown")

# 5. Launch our application
def main() -> None:
    if not BOT_TOKEN:
        logger.critical("CRITICAL ERROR: TELEGRAM_BOT_TOKEN is missing from your .env file!")
        return

    logger.info("Initializing TOBI-XAUUSD Menu Engine...")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )

    # Register '/start' Command Handler
    app.add_handler(CommandHandler("start", start_command))
    
    # Register Text Message Handler to detect button clicks
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_clicks))

    logger.info("Bot is active and polling for interactive button inputs...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()