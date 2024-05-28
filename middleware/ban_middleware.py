from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from app.database.requests import check_user_banned

class CheckUserBannedMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:

        user_id = event.from_user.id
        is_banned = await check_user_banned(user_id)
        if is_banned:
            await event.answer("Извините, вы заблокированы и не можете выполнить эту команду.")
            return
        return await handler(event, data)