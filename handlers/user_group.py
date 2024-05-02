import os
from string import punctuation
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from dotenv import load_dotenv

from filters.chat_type import ChatTypeFilter
from aiogram.filters import CommandStart, Command, Filter
from aiogram import Bot
import app.keyboards as kb
from app.database.requests import get_all_orders, get_driver

user_group_router = Router()
user_group_router.message.filter(ChatTypeFilter(['group', 'supergroup']))
load_dotenv()

restricted_words = {'кабан', 'хомяк', 'выпухоль'}


# def clean_text(text: str):
#     return text.translate(str.maketrans('', '', punctuation))

# @user_group_router.message()
# async def cleaner(message: Message):
#     if restricted_words.intersection(message.text.lower().split()):
#         await message.answer(f'{message.from_user.first_name}, соблюдайте порядок чата')
#         await message.delete()

# @user_group_router.message(CommandStart())
# async def cmd_start(message: Message):
#     await message.answer(f'{message.chat.id}')

@user_group_router.callback_query(F.data.startswith('accept_'))
async def accept(callback: CallbackQuery, bot: Bot):
    await callback.answer('')
    order_id = await get_all_orders(callback.data.split('_')[1])
    driver = await get_driver(callback.from_user.id)
    await callback.message.edit_text(f'<i><b>Заказ № {order_id.id}</b></i>\n'
                                     f'Принял -  {callback.from_user.first_name} \n'
                                     f'Номер телефона  +{order_id.phone}')
    await bot.send_photo(chat_id=order_id.tg_id, photo=driver.photo_car, caption=f'За вами приедет {driver.car_name}')
    await bot.send_message(chat_id=callback.from_user.id,
                           text=callback.message.text,
                           reply_markup=await kb.close_and_finish(order_id.id))


@user_group_router.callback_query(F.data.startswith('close_'))
async def accept(callback: CallbackQuery, bot: Bot):
    await callback.answer('')
    order_id = await get_all_orders(callback.data.split('_')[1])
    await callback.message.edit_text(f'Ты отказался от заказа №{order_id.id}')
    await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                           text=f'Водитель {callback.from_user.first_name} отменил выпонление заказа\n'
                                f'{callback.message.text}\n',
                           reply_markup=await kb.accept(order_id.id))

    await bot.send_message(chat_id=order_id.tg_id,
                           text=f'Ожидайте ⌛\n'
                                f'Будет назначен новый водитель>\n')


@user_group_router.callback_query(F.data.startswith('finish_'))
async def accept(callback: CallbackQuery, bot: Bot):
    await callback.answer('')
    order_id = await get_all_orders(callback.data.split('_')[1])
    await callback.message.edit_text(f'Заказ выполнен {order_id.id}')
    await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                           text=f"Заказ № {order_id.id} выполнен ✅\n\n"
                                f"Водителем {callback.from_user.first_name}")
    await bot.send_message(chat_id=order_id.tg_id,
                           text=f'Заказ выполнен✅.\n '
                                f'Спасибо что пользуетесь нашими услугами 🙏\n ')
