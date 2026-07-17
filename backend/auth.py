import logging
from enum import Enum

# Setup modular logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class UserRole(Enum):
    GUEST = "guest"
    USER = "user"
    ADMIN = "admin"

class LicenseTier(Enum):
    FREE = "free"
    PREMIUM = "premium"
    LIFETIME = "lifetime"

class SecurityGatekeeper:
    """
    Centralized authorization rules for the TOBI-XAUUSD ecosystem.
    Provides decoupled middleware checks for user actions.
    """

    @staticmethod
    def is_admin(user_profile: dict) -> bool:
        """
        Returns True if the user is an authorized Administrator.
        """
        if not user_profile:
            return False
        
        role = user_profile.get("role", "guest")
        return role == UserRole.ADMIN.value

    @staticmethod
    def has_active_subscription(user_profile: dict) -> bool:
        """
        Checks if the user has a Premium or Lifetime license.
        """
        if not user_profile:
            return False
            
        tier = user_profile.get("license_tier", "free")
        allowed_tiers = [LicenseTier.PREMIUM.value, LicenseTier.LIFETIME.value]
        
        return tier in allowed_tiers

    @staticmethod
    def check_access(user_profile: dict, required_tier: LicenseTier) -> tuple[bool, str]:
        """
        Core gatekeeper logic.
        Evaluates permissions and returns authorization state alongside response messaging.
        """
        if not user_profile:
            return False, "❌ Account profile not found. Please type `/start` to register."
            
        # Admins bypass all licensing checks
        if SecurityGatekeeper.is_admin(user_profile):
            return True, "Authorized (Bypass: Admin privileges)"

        user_tier = user_profile.get("license_tier", "free")

        # Check Premium requirements
        if required_tier == LicenseTier.PREMIUM:
            if user_tier in [LicenseTier.PREMIUM.value, LicenseTier.LIFETIME.value]:
                return True, "Authorized"
            return False, (
                "⚠️ **Access Denied: Premium Feature**\n\n"
                "The requested module is reserved for **Premium Members** only.\n\n"
                "Please upgrade your subscription status in **👤 My Profile**."
            )

        # Standard Free/Guest checks pass by default
        return True, "Authorized"