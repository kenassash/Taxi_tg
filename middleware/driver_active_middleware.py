from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, CallbackQuery
from app.database.requests import get_driver

class DriverActiveMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, CallbackQuery) and event.data.startswith('accept_'):
            driver = await get_driver(event.from_user.id)
            if not driver.active:
                await event.answer("Вы не активны и не можете принимать заказы.", show_alert=True)
                return
        return await handler(event, data)
