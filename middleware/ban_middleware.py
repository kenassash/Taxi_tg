from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
from app.database.requests import check_user_banned
from app.dialog.states import SendMessage


class CheckUserBannedMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:

        user_id = event.from_user.id
        is_banned = await check_user_banned(user_id)
        if isinstance(event, Message):  # Проверяем, что это текстовое сообщение
            state: FSMContext = data.get("state")
            if event.text and event.text.startswith("/manager"):
                return await handler(event, data)  # Разрешаем /manager
            if state:
                current_state = await state.get_state()
                if current_state == SendMessage.send_manager:
                    return await handler(event, data)

            user_id = event.from_user.id
            is_banned = await check_user_banned(user_id)
            if is_banned:
                await event.answer("🚫 Извините, вы заблокированы и не можете выполнить эту команду.")
                return

        return await handler(event, data)