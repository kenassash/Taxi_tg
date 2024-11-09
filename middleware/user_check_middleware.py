from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, message
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
        try:
            # drivers = await get_driver(user_id)
            # if drivers and drivers.tg_id == user_id:
            #     data['role'] = 'driver'
            #     data['driver'] = drivers
            user = await get_user(user_id)
            if user:
                data['role'] = 'user'
                data['user'] = user
            else:
                data['role'] = 'guest'
                # Проверка, зарегистрирован ли пользователь
                # user = await get_user(user_id)
                # if user:

        except KeyError:
            await event.answer('Ошибка: роль пользователя не определена. Попробуйте заново')
        except Exception as e:
            await event.answer('Ошибка: роль пользователя не определена. Попробуйте заново')

        return await handler(event, data)
