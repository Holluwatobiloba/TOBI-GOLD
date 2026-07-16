import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 1. Setup system-wide logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# 3. Define the start command response
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends a professional welcome message when a user interacts with TOBI-XAUUSD.
    """
    welcome_text = (
        "📈 **TOBI-XAUUSD Engine Online** 📈\n\n"
        "Welcome to your professional gold trading command center.\n\n"
        "This platform is designed to deliver automated analytics, real-time "
        "signals, and advanced risk tracking specifically for XAUUSD spot gold trading.\n\n"
        "Use `/help` to see available commands (development in progress)."
    )
    await update.message.reply_text(text=welcome_text, parse_mode="Markdown")

# 4. Main function with resilient network timeouts
def main() -> None:
    if not BOT_TOKEN:
        logger.critical("CRITICAL ERROR: TELEGRAM_BOT_TOKEN is missing from your .env file!")
        return

    # Visual Masking Check to verify token length and format
    masked_token = f"{BOT_TOKEN[:4]}...{BOT_TOKEN[-4:]}" if len(BOT_TOKEN) > 10 else "INVALID"
    logger.info(f"Using Secret Token: {masked_token}")
    logger.info("Initializing Resilient TOBI-XAUUSD Bot Application...")

    # We build the application with high-tolerance timeouts (30 seconds)
    # to survive slower DNS resolutions and local network fluctuations.
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)  # Increase initial connection timeout (Default is 5.0)
        .read_timeout(30.0)     # Increase read response timeout (Default is 5.0)
        .build()
    )

    # Register command handler
    app.add_handler(CommandHandler("start", start_command))

    logger.info("Bot configuration locked. Initiating connection...")
    
    # Run polling and instruct it to drop any backed-up network queries
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()