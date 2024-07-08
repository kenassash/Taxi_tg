from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def shop_order():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='ДОСТАВКА', callback_data='shoporder'))
    return keyboard.adjust().as_markup()


async def shop_price():
    keyboard = InlineKeyboardBuilder()
    for price in range(200, 850, 50):
        keyboard.add(InlineKeyboardButton(text=str(price), callback_data=f'shopprice_{price}'))
    keyboard.add(InlineKeyboardButton(text='Написать адрес', callback_data='shop_point_end'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))

    return keyboard.adjust(4, 4, 4, 1, 1, 1).as_markup()
