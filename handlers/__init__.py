"""Import all routers and add them to routers_list."""

from .handlers import router
from .driver_handlers import driver_router
from .shop_hanlders import shop_router
from .user_group import user_group_router

routers_list = [
    router,
    driver_router,
    shop_router,
    user_group_router
]

__all__ = [
    "routers_list",
]
