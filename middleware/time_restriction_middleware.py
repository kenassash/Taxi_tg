import asyncio
import os
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, Update
from datetime import datetime, time
import pytz
from dotenv import load_dotenv
load_dotenv()


class TimeRestrictionMiddleware(BaseMiddleware):

    def __init__(self):
        self.start_time = time(23, 0)
        self.end_time = time(7, 0)
        self.timezone = pytz.timezone('Asia/Yakutsk')
        self.active = True  # По умолчанию middleware активна


    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        print(f"Middleware active status: {self.active}")
        if not self.active:
            return await handler(event, data)

        # user_id = None
        # if isinstance(event, Update) and event.message:
        #     user_id = event.message.from_user.id
        # elif isinstance(event, Update) and event.callback_query:
        #     user_id = event.callback_query.from_user.id

        # if event.from_user.id in [int(os.getenv('CHAT_ID_ADMIN'))]:
        #     return await handler(event, data)

        # Получение текущего времени в заданном часовом поясе
        current_time = datetime.now(self.timezone).time()

        # Вывод текущего времени в консоль
        print(f"ASIA time: {current_time}")

        if current_time >= self.start_time or current_time < self.end_time:
            if isinstance(event, Message):
                await event.answer("Извините, но отправка сообщений возможна только с 7:00 до 23:00.")
            return  # Прерываем обработку сообщения

        return await handler(event, data)

    def activate(self):
        self.active = True


    def deactivate(self):
        self.active = False
