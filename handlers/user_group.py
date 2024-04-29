from string import punctuation
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from filters.chat_type import ChatTypeFilter
from aiogram.filters import CommandStart, Command, Filter
from aiogram import Bot
import app.keyboards as kb
from app.database.requests import set_user, set_order, get_all_orders

user_group_router = Router()
user_group_router.message.filter(ChatTypeFilter(['group', 'supergroup']))

restricted_words = {'кабан', 'хомяк', 'выпухоль'}

# def clean_text(text: str):
#     return text.translate(str.maketrans('', '', punctuation))
#
#
# @user_group_router.message()
# async def cleaner(message: Message):
#     if restricted_words.intersection(message.text.lower().split()):
#         await message.answer(f'{message.from_user.first_name}, соблюдайте порядок чата')
#         await message.delete()


@user_group_router.callback_query(F.data.startswith('accept_'))
async def accept(callback: CallbackQuery, bot: Bot):
    await callback.answer('')
    order_id = await get_all_orders(callback.data.split('_')[1])
    await callback.message.edit_text(f'Заказ принял -  {callback.from_user.first_name} \n'
                                        f'Номер телефона  +{order_id.phone}',
                                     reply_markup=await kb.close())



@user_group_router.callback_query(F.data == 'close_')
async def accept(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.answer('Ты отказался')

