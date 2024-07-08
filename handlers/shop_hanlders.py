import os
import re

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv

from app.database.requests import get_all_orders, get_driver, delete_order_execution, delete_order_pass, \
    get_order_driver, get_user, set_order, shop_order_add
from filters.chat_type import ChatTypeFilter
import app.keyboards as kb
import app.kb.kb_shop as kb_sh

shop_router = Router()
shop_router.message.filter(ChatTypeFilter(['private']))
load_dotenv()


@shop_router.callback_query(F.data == 'shoporder')
async def shop_add_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer('')
    await callback.message.edit_text(f"Выберите ценну или куда поедите",
                                     reply_markup=await kb_sh.shop_price())


@shop_router.callback_query(F.data.startswith('shopprice_'))
async def shop_price(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer('')
    user_id = await get_user(callback.from_user.id)
    price = callback.data.split('_')[1]
    data = {
        'point_start': 'Магазин ' + user_id.shop_name,
        'point_end': 'Магазин ' + user_id.shop_name,
        'price': price
    }
    order_id = await set_order(user_id.id, data)
    order_data = await get_all_orders(order_id)
    message_id = None

    sent_driver_message = await callback.message.edit_text(f"<b>Ожидайте водителя⌛</b>",
                                                           reply_markup=await kb.delete_order(order_id, message_id))

    sent_message = await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                          text=f"Магазин '<b>{user_id.shop_name}</b>' доставка!\n"
                                               f"Цена: <b>{price}Р</b>",
                                          reply_markup=await kb.accept(order_id, sent_driver_message.message_id))
    await state.clear()
    await state.update_data(message_id=sent_message.message_id)


class ShopPointend(StatesGroup):
    send_pont_end = State()
    price_shop = State()


@shop_router.callback_query(F.data == 'shop_point_end')
async def shop_add_point(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await callback.answer('')
    await callback.message.edit_text(f"Напишите куда доставка",
                                     reply_markup=await kb.cancel_order())
    await state.set_state(ShopPointend.send_pont_end)


@shop_router.message(ShopPointend.send_pont_end, F.text)
async def shop_point_end_addres(message: Message, state: FSMContext):
    if message.text:
        await state.update_data(point_end=message.text)
        await message.answer(f'Введите сумму за доставку')
        await state.set_state(ShopPointend.price_shop)
    else:
        await message.answer('Вы ввели не корретно адрес')


@shop_router.message(ShopPointend.price_shop, F.text)
async def shop_point_end_addres(message: Message, state: FSMContext, bot: Bot):
    input_int = message.text.strip()
    pattern = r"^\d+$"
    if re.match(pattern, input_int):
        await state.update_data(price=input_int)
        data = await state.get_data()
        data.update({'point_start': 'Магазин'})
        user_id = await get_user(message.from_user.id)
        order_id = await set_order(user_id.id, data)
        message_id = None
        sent_driver_message = await message.answer(f"<b>Ожидайте водителя⌛</b>",
                                                   reply_markup=await kb.delete_order(order_id, message_id))
        sent_message = await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                              text=f"Магазин '<b>{user_id.shop_name}</b>' доставка!\n"
                                                   f"Конечная точка: <b>{data['point_end']}</b>\n\n"
                                                   f"Цена: <b>{data['price']}Р</b>",
                                              reply_markup=await kb.accept(order_id, sent_driver_message.message_id))

        await state.clear()
        await state.update_data(message_id=sent_message.message_id)
    else:
        await message.answer("Пожалуйста, введите только цифры.")
