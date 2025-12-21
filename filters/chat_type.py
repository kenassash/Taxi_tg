from aiogram.filters import Filter
from aiogram import Bot, types
from aiogram.types import Message, CallbackQuery


class ChatTypeFilter(Filter):
    def __init__(self, chat_types: list[str]) -> None:
        self.chat_types = chat_types

    async def __call__(self, event, **kwargs) -> bool:
        # Проверяем тип события
        if isinstance(event, Message):
            return event.chat.type in self.chat_types
        elif isinstance(event, CallbackQuery):
            # Для callback_query проверяем chat из message
            if event.message:
                return event.message.chat.type in self.chat_types
        return False


class IsAdmin(Filter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        return message.from_user.id in bot.my_admins_list