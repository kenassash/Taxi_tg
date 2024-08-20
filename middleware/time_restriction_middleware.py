import asyncio
import os
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, Update
from datetime import datetime, time
import pytz





class TimeRestrictionMiddleware(BaseMiddleware):

    def __init__(self):
        # self.start_time = time(23, 00)
        # self.end_time = time(7, 0)
        # self.timezone = pytz.timezone('Asia/Yakutsk')
        self.active = False  # По умолчанию middleware активна

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        if not self.active:
            return await handler(event, data)
        else:
            await event.answer("Извините, но отправка сообщений временно недоступна")
            return

        # # Получение текущего времени в заданном часовом поясе
        # current_time = datetime.now(self.timezone).time()
        #
        # # Вывод текущего времени в консоль
        # print(f"ASIA time: {current_time}")
        #
        # if (current_time >= self.start_time or current_time < self.end_time):
        #     if isinstance(event, Message):
        #         await event.answer("Извините, но отправка сообщений временно не доступна")
        #     return  # Прерываем обработку сообщения
        #
        # return await handler(event, data)

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False
