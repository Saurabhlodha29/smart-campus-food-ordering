"""
Import all models so Base.metadata is fully populated before Alembic runs.
Every new model file must be added here.
"""
from app.models.role import Role  # noqa: F401
from app.models.campus import Campus  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.outlet import Outlet  # noqa: F401
from app.models.menu_item import MenuItem  # noqa: F401
from app.models.pickup_slot import PickupSlot  # noqa: F401
from app.models.order import Order  # noqa: F401
from app.models.order_item import OrderItem  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.outlet_payout import OutletPayout  # noqa: F401
from app.models.outlet_rating import OutletRating  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.email_otp_token import EmailOtpToken  # noqa: F401
from app.models.admin_application import AdminApplication  # noqa: F401
from app.models.outlet_application import OutletApplication  # noqa: F401
from app.models.verification_report import VerificationReport  # noqa: F401

__all__ = [
    "Role",
    "Campus",
    "User",
    "Outlet",
    "MenuItem",
    "PickupSlot",
    "Order",
    "OrderItem",
    "Payment",
    "OutletPayout",
    "OutletRating",
    "Notification",
    "EmailOtpToken",
    "AdminApplication",
    "OutletApplication",
    "VerificationReport",
]
