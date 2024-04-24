from string import punctuation
from aiogram import Router
from aiogram.types import Message
from filters.chat_type import ChatTypeFilter

user_group_router = Router()
user_group_router.message.filter(ChatTypeFilter(['group', 'supergroup']))

restricted_words = {'кабан', 'хомяк', 'выпухоль'}

def clean_text(text: str):
    return text.translate(str.maketrans('', '', punctuation))


@user_group_router.message()
async def cleaner(message: Message):
    if restricted_words.intersection(message.text.lower().split()):
        await message.answer(f'{message.from_user.first_name}, соблюдайте порядок чата')
        await message.delete()