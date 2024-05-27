from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.requests import shop_check
import app.keyboards as kb


# Декоратор для проверки статуса блокировки пользователя
def shop_decorator(func):
    async def wrapper(message: Message, state: FSMContext):
        # Получаем ID пользователя из сообщения
        user_id = message.from_user.id
        shop_user = await shop_check(user_id)
        if shop_user:
            await message.answer(f"Добро пожаловать, Магазин",
                                 reply_markup=await kb.shop_order())
        else:
            # Если пользователь не заблокирован, выполняем команду
            await func(message, state)
    return wrapper

