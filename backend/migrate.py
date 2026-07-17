import os
import logging
import psycopg2
from dotenv import load_dotenv

# 1. Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "schema.sql"))

def run_database_migrations() -> bool:
    """
    Reads the SQL schema blueprint and executes it on the PostgreSQL server.
    """
    logger.info("--- Starting TOBI-XAUUSD Migration Pipeline ---")
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL is missing from environment. Migration aborted.")
        return False

    if not os.path.exists(SCHEMA_PATH):
        logger.error(f"Migration failed: Schema file not found at {SCHEMA_PATH}")
        return False

    connection = None
    try:
        # Read the raw SQL commands from our blueprint
        logger.info(f"Reading database blueprint from: {SCHEMA_PATH}")
        with open(SCHEMA_PATH, "r") as file:
            sql_script = file.read()

        # Connect directly to our PostgreSQL server
        logger.info("Connecting to PostgreSQL database engine...")
        connection = psycopg2.connect(DATABASE_URL)
        cursor = connection.cursor()

        # Execute the SQL commands
        logger.info("Injecting SQL schema tables and index structures...")
        cursor.execute(sql_script)

        # Commit the changes to write them permanently
        connection.commit()
        logger.info("🎉 Database tables successfully created!")

        cursor.close()
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed with critical error: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    run_database_migrations()