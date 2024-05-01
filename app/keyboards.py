from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

main = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Создать заказ', callback_data='neworder')]])

async def geolocate_point_start():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Определить место положение 🌐', request_location=True),]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard
async def phone():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Отправь номер телефона ☎️', request_contact=True), ]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    return keyboard

async def accept(order_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Принять заказ', callback_data=f'accept_{order_id}'))
    return keyboard.adjust().as_markup()

async def close_and_finish(order_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Завершить ✅', callback_data=f'finish_{order_id}'))
    keyboard.add(InlineKeyboardButton(text='Отказаться ❌', callback_data=f'close_{order_id}'))
    return keyboard.adjust(2).as_markup()


async def cancel_order():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Отменить заказ', callback_data=f'cancelorder_'))
    return keyboard.adjust().as_markup()

