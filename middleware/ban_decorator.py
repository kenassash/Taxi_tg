from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.requests import check_user_banned


# Декоратор для проверки статуса блокировки пользователя
def user_not_banned(func):
    async def wrapper(message: Message, state: FSMContext):
        # Получаем ID пользователя из сообщения
        user_id = message.from_user.id
        # Проверяем статус блокировки пользователя
        is_banned = await check_user_banned(user_id)
        if is_banned:
            await message.answer("Извините, вы заблокированы и не можете выполнить эту команду.")
        else:
            # Если пользователь не заблокирован, выполняем команду
            await func(message, state)
    return wrapper

