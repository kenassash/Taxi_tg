import asyncio
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from app.database.requests import shop_check
import app.kb.kb_shop as kb_sh

class ShopMiddleware(BaseMiddleware):

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user_id = event.from_user.id
            shop_user = await shop_check(user_id)
            if shop_user:
                await event.answer("Добро пожаловать, Магазин", reply_markup=await kb_sh.shop_order())
                return
        return await handler(event, data)
