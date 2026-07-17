import os
import logging
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configurations
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

class DatabaseManager:
    """
    Manages the PostgreSQL Connection Pool and executes all SQL operations
    securely for users and trade signals.
    """
    _connection_pool = None

    @classmethod
    def initialize_pool(cls):
        """
        Initializes a thread-safe connection pool using the database URL.
        """
        if not DATABASE_URL:
            logger.critical("DATABASE_URL is missing from environment variables!")
            return

        if cls._connection_pool is None:
            try:
                logger.info("Initializing PostgreSQL Connection Pool...")
                cls._connection_pool = pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=10,
                    dsn=DATABASE_URL
                )
                logger.info("PostgreSQL Connection Pool initialized successfully!")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                cls._connection_pool = None

    @classmethod
    def register_or_get_user(cls, telegram_id: int, username: str, first_name: str) -> dict:
        """
        Registers a new user in the database if they do not exist.
        If they exist, returns their profile.
        """
        if not cls._connection_pool:
            cls.initialize_pool()
            if not cls._connection_pool:
                logger.error("Pool uninitialized. Registration failed.")
                return {}

        connection = None
        try:
            connection = cls._connection_pool.getconn()
            cursor = connection.cursor()

            # Insert new user or do nothing if they already exist
            insert_query = """
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE 
            SET username = EXCLUDED.username, first_name = EXCLUDED.first_name
            RETURNING telegram_id, username, first_name, role, license_tier, registered_at;
            """
            
            cursor.execute(insert_query, (telegram_id, username, first_name))
            result = cursor.fetchone()
            connection.commit()
            cursor.close()

            if result:
                return {
                    "telegram_id": result[0],
                    "username": result[1],
                    "first_name": result[2],
                    "role": result[3],
                    "license_tier": result[4],
                    "registered_at": result[5]
                }
            return {}
        except Exception as e:
            logger.error(f"Database error during user registration: {e}")
            if connection:
                connection.rollback()
            return {}
        finally:
            if connection:
                cls._connection_pool.putconn(connection)

    @classmethod
    def update_user_activity(cls, telegram_id: int) -> bool:
        """
        Updates the last_active timestamp for a user.
        """
        if not cls._connection_pool:
            return False

        connection = None
        try:
            connection = cls._connection_pool.getconn()
            cursor = connection.cursor()
            
            query = """
            UPDATE users 
            SET last_active = CURRENT_TIMESTAMP 
            WHERE telegram_id = %s;
            """
            cursor.execute(query, (telegram_id,))
            connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Failed to update user activity: {e}")
            if connection:
                connection.rollback()
            return False
        finally:
            if connection:
                cls._connection_pool.putconn(connection)

    @classmethod
    def create_signal(cls, direction: str, entry: float, sl: float, tp: float, created_by: int, notes: str = None) -> int:
        """
        Inserts a new gold trading signal into the signals table.
        Returns the generated signal_id.
        """
        if not cls._connection_pool:
            return 0

        connection = None
        try:
            connection = cls._connection_pool.getconn()
            cursor = connection.cursor()

            query = """
            INSERT INTO signals (pair, direction, entry_price, stop_loss, take_profit, created_by, notes)
            VALUES ('XAUUSD', %s, %s, %s, %s, %s, %s)
            RETURNING signal_id;
            """
            
            cursor.execute(query, (direction, entry, sl, tp, created_by, notes))
            signal_id = cursor.fetchone()[0]
            connection.commit()
            cursor.close()
            return signal_id
        except Exception as e:
            logger.error(f"Failed to create trade signal: {e}")
            if connection:
                connection.rollback()
            return 0
        finally:
            if connection:
                cls._connection_pool.putconn(connection)

    @classmethod
    def get_active_signals(cls) -> list:
        """
        Retrieves all currently active setups from the database.
        """
        if not cls._connection_pool:
            return []

        connection = None
        try:
            connection = cls._connection_pool.getconn()
            cursor = connection.cursor()

            query = """
            SELECT signal_id, pair, direction, entry_price, stop_loss, take_profit, status, notes
            FROM signals
            WHERE status = 'active'
            ORDER BY signal_id DESC;
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()

            signals = []
            for row in rows:
                signals.append({
                    "signal_id": row[0],
                    "pair": row[1],
                    "direction": row[2],
                    "entry_price": float(row[3]),
                    "stop_loss": float(row[4]),
                    "take_profit": float(row[5]),
                    "status": row[6],
                    "notes": row[7]
                })
            return signals
        except Exception as e:
            logger.error(f"Failed to query active signals: {e}")
            return []
        finally:
            if connection:
                cls._connection_pool.putconn(connection)

    @classmethod
    def update_signal_status(cls, signal_id: int, status: str) -> bool:
        """
        Updates the status of a signal (e.g. tp_hit, sl_hit, cancelled).
        """
        if not cls._connection_pool:
            return False

        connection = None
        try:
            connection = cls._connection_pool.getconn()
            cursor = connection.cursor()

            query = """
            UPDATE signals
            SET status = %s, closed_at = CURRENT_TIMESTAMP
            WHERE signal_id = %s;
            """
            
            cursor.execute(query, (status, signal_id))
            connection.commit()
            
            # Check if any row was actually updated
            row_count = cursor.rowcount
            cursor.close()
            return row_count > 0
        except Exception as e:
            logger.error(f"Failed to update signal status: {e}")
            if connection:
                connection.rollback()
            return False
        finally:
            if connection:
                cls._connection_pool.putconn(connection)

    @classmethod
    def get_signal_statistics(cls) -> dict:
        """
        Aggregates metrics from the signals table to compute historical performance.
        Returns a dictionary of total trades, wins, losses, and calculated win rate.
        """
        if not cls._connection_pool:
            logger.error("Database pool is uninitialized. Statistics aggregation failed.")
            return {}

        connection = None
        try:
            connection = cls._connection_pool.getconn()
            cursor = connection.cursor()

            query = """
            SELECT 
                COUNT(*) AS total_signals,
                COUNT(CASE WHEN status = 'tp_hit' THEN 1 END) AS total_wins,
                COUNT(CASE WHEN status = 'sl_hit' THEN 1 END) AS total_losses,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) AS total_cancelled,
                COUNT(CASE WHEN status IN ('pending', 'active') THEN 1 END) AS total_running
            FROM signals;
            """
            
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()

            if result:
                total, wins, losses, cancelled, running = result
                closed_trades = wins + losses
                
                # Calculate dynamic win rate (avoid division by zero if no closed trades yet)
                win_rate = (wins / closed_trades * 100) if closed_trades > 0 else 0.0

                return {
                    "total_signals": total,
                    "wins": wins,
                    "losses": losses,
                    "cancelled": cancelled,
                    "running": running,
                    "closed_trades": closed_trades,
                    "win_rate": round(win_rate, 1)
                }
            return {}
        except Exception as e:
            logger.error(f"Error computing performance metrics: {e}")
            return {}
        finally:
            if connection:
                cls._connection_pool.putconn(connection)