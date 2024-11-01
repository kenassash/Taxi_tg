from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from app.database.requests import get_driver, get_user

class UserCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id

        # Проверка, является ли пользователь таксистом
        drivers = await get_driver(user_id)
        if drivers and drivers.tg_id == user_id:
            data['role'] = 'driver'
            data['driver'] = drivers
        else:
            # Проверка, зарегистрирован ли пользователь
            user = await get_user(user_id)
            if user:
                data['role'] = 'user'
                data['user'] = user
            else:
                data['role'] = 'guest'

        return await handler(event, data)
