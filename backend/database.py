import os
import logging
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

# 1. Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. Load configurations
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

class DatabaseManager:
    """
    Manages our PostgreSQL database connection pool and core queries.
    """
    _connection_pool = None

    @classmethod
    def initialize_pool(cls) -> bool:
        """
        Creates a connection pool so multiple app queries can run concurrently.
        """
        if not DATABASE_URL:
            logger.error("DATABASE_URL is missing from environment configurations!")
            return False
            
        try:
            logger.info("Initializing PostgreSQL Connection Pool...")
            cls._connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DATABASE_URL
            )
            logger.info("Database Connection Pool successfully created!")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            return False

    @classmethod
    def test_connection(cls) -> bool:
        """
        Attempts to grab a connection from our pool and run a basic diagnostics query.
        """
        if not cls._connection_pool:
            logger.error("Cannot test connection. Pool is not initialized.")
            return False

        connection = None
        try:
            connection = cls._connection_pool.getconn()
            cursor = connection.cursor()
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()
            logger.info(f"Database handshake successful! Engine Version: {db_version[0]}")
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Database query test failed: {e}")
            return False
        finally:
            if connection:
                cls._connection_pool.putconn(connection)

    @classmethod
    def register_or_get_user(cls, telegram_id: int, username: str, first_name: str) -> dict:
        """
        Checks if a user exists in our database.
        If they do not, it creates a new record for them.
        Returns the user's database record (role, license_tier, etc.).
        """
        if not cls._connection_pool:
            logger.error("Database pool is uninitialized. Registration failed.")
            return {}

        connection = None
        try:
            connection = cls._connection_pool.getconn()
            cursor = connection.cursor()

            # Security Check: Parameterized SQL prevents injection attacks
            # This query tries to insert a user, but if their ID exists, it does nothing
            query = """
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE 
            SET username = EXCLUDED.username, first_name = EXCLUDED.first_name
            RETURNING telegram_id, username, first_name, role, license_tier;
            """
            
            # Execute with safe tuple arguments
            cursor.execute(query, (telegram_id, username, first_name))
            user_data = cursor.fetchone()
            
            # Save our changes securely
            connection.commit()
            cursor.close()

            if user_data:
                return {
                    "telegram_id": user_data[0],
                    "username": user_data[1],
                    "first_name": user_data[2],
                    "role": user_data[3],
                    "license_tier": user_data[4]
                }
            return {}

        except Exception as e:
            logger.error(f"Error registering user {telegram_id}: {e}")
            if connection:
                connection.rollback() # Rollback changes to keep data clean
            return {}
        finally:
            if connection:
                cls._connection_pool.putconn(connection)

    @classmethod
    def update_user_activity(cls, telegram_id: int) -> bool:
        """
        Updates the last active timestamp of a user in the database.
        """
        if not cls._connection_pool:
            return False

        connection = None
        try:
            connection = cls._connection_pool.getconn()
            cursor = connection.cursor()

            query = """
            UPDATE users 
            SET last_active_at = CURRENT_TIMESTAMP 
            WHERE telegram_id = %s;
            """
            
            cursor.execute(query, (telegram_id,))
            connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Error updating activity for {telegram_id}: {e}")
            if connection:
                connection.rollback()
            return False
        finally:
            if connection:
                cls._connection_pool.putconn(connection)

def run_diagnostics():
    """
    Independent script runner to check connection state.
    """
    logger.info("--- Starting TOBI-XAUUSD Database Diagnostics ---")
    initialized = DatabaseManager.initialize_pool()
    if initialized:
        DatabaseManager.test_connection()
    else:
        logger.error("Database initialization aborted due to pool failures.")

if __name__ == "__main__":
    run_diagnostics()