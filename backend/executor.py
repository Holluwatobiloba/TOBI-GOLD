import rpyc
import logging

logger = logging.getLogger(__name__)

class MetaTraderExecutor:
    def __init__(self, host="mt5_bridge", port=8001):
        """Establishes an RPyC pipeline straight into the containerized Wine terminal"""
        self.host = host
        self.port = port
        self.mt5 = None
        self._connect()

    def _connect(self):
        try:
            # Connect via the remote procedure proxy network
            conn = rpyc.classic.connect(self.host, self.port)
            self.mt5 = conn.modules['MetaTrader5']
            
            # Initialize MT5 within the Wine container context
            if not self.mt5.initialize():
                logger.error(f"MT5 initialization failed inside container. Error: {self.mt5.last_error()}")
                self.mt5 = None
            else:
                logger.info("Successfully established connection to containerized MetaTrader 5 terminal!")
        except Exception as e:
            logger.error(f"Could not connect to MT5 Bridge server via RPyC: {e}")
            self.mt5 = None

    def execute_market_order(self, symbol, order_type, volume, price, sl, tp):
        """Constructs and delivers a real-time market execution order to your Demo broker account"""
        if not self.mt5:
            logger.warning("Attempting reconnection to MT5 execution bridge...")
            self._connect()
            if not self.mt5:
                logger.error("Execution canceled: MT5 bridge container is unreachable.")
                return False

        # Normalize typical broker symbols (e.g., XAUUSD or Gold Futures equivalents)
        # Most MT5 brokers use "XAUUSD" for spot gold
        broker_symbol = "XAUUSD" if symbol == "GC=F" else symbol

        # Map execution directions to MT5 specific constants
        direction = self.mt5.ORDER_TYPE_BUY if order_type.upper() == "BUY" else self.mt5.ORDER_TYPE_SELL
        
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": broker_symbol,
            "volume": float(volume),
            "type": direction,
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 202607,  # Bot tracking ID identifier
            "comment": "Tobi 80/20 Quantitative Engine",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

        logger.info(f"Sending order request to MT5: {order_type} {volume} lots on {broker_symbol}...")
        result = self.mt5.order_send(request)
        
        if result is None:
            logger.error("Critical: MT5 order_send returned None. System communication failure.")
            return False

        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            logger.error(f"Broker rejected trade! Return Error Code: {result.retcode}. Description: {result.comment}")
            return False

        logger.info(f"⚡ BROKER TRADED HANDS-FREE! Order ID: #{result.order} filled at {result.price}")
        return True