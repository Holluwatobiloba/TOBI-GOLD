import logging

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class RiskManager:
    """
    Handles mathematical risk management operations, specifically calculating
    ideal lot sizes for Gold (XAUUSD) trades.
    """

    @staticmethod
    def calculate_gold_position_size(
        balance: float, 
        risk_percent: float, 
        entry: float, 
        stop_loss: float
    ) -> dict:
        """
        Calculates the recommended lot size on XAUUSD.
        
        - 1 Standard Lot of Gold = 100oz.
        - A $0.10 price movement represents 1 Pip.
        - Therefore, 1.0 point movement (e.g., from 2390.00 to 2391.00) is 10 Pips.
        - The value of 1 pip for 1.0 lot of XAUUSD is $1.00.
        """
        try:
            if balance <= 0 or risk_percent <= 0:
                raise ValueError("Balance and Risk Percentage must be greater than zero.")

            # Calculate total cash amount to risk
            cash_risk = balance * (risk_percent / 100.0)

            # Get absolute price distance to stop loss
            price_distance = abs(entry - stop_loss)
            if price_distance == 0:
                raise ValueError("Entry price and Stop Loss cannot be identical.")

            # Convert price distance to gold pips (1 pip = $0.10 movement)
            pips_at_risk = price_distance * 10

            # XAUUSD lot size formula: Cash Risk / (Pips * Pip Value)
            # Since 1 pip = $1.00 of risk on a standard 1.0 lot, Pip Value = 1.0
            raw_lot_size = cash_risk / (pips_at_risk * 1.0)
            
            # Round to 2 decimal places (Micro-lots are the minimum size on retail MT4/MT5 platforms)
            recommended_lots = round(raw_lot_size, 2)

            return {
                "status": "success",
                "cash_risk": round(cash_risk, 2),
                "pips_at_risk": int(pips_at_risk),
                "recommended_lots": max(0.01, recommended_lots)  # Minimum size is 0.01
            }

        except Exception as e:
            logger.error(f"Failed to compute position risk: {e}")
            return {
                "status": "error",
                "message": str(e)
            }