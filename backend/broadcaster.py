import os
import logging
import asyncio
import psycopg2
from dotenv import load_dotenv
from telegram import Bot

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

class SignalBroadcaster:
    """
    Handles background broadcasting of trade signals to all registered bot users.
    """
    
    @staticmethod
    def get_all_active_users() -> list:
        """
        Retrieves all user Telegram IDs from the database.
        """
        if not DATABASE_URL:
            logger.error("DATABASE_URL is missing!")
            return []
            
        connection = None
        try:
            connection = psycopg2.connect(DATABASE_URL)
            cursor = connection.cursor()
            cursor.execute("SELECT telegram_id FROM users;")
            rows = cursor.fetchall()
            cursor.close()
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch user list for broadcast: {e}")
            return []
        finally:
            if connection:
                connection.close()

    @classmethod
    async def broadcast_message(cls, text: str) -> None:
        """
        Asynchronously sends a formatted text message to all registered users.
        """
        if not BOT_TOKEN:
            logger.critical("BOT_TOKEN is missing from environment!")
            return

        user_ids = cls.get_all_active_users()
        if not user_ids:
            logger.info("No registered users to broadcast to.")
            return

        logger.info(f"Initiating global broadcast to {len(user_ids)} users...")
        bot = Bot(token=BOT_TOKEN)

        for user_id in user_ids:
            try:
                await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
                logger.info(f"Broadcast successfully sent to user: {user_id}")
                # Small delay to respect Telegram's rate limits (max 30 messages per second)
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.warning(f"Could not send broadcast to {user_id}: {e}")