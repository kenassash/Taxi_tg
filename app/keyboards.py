from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder

main = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Создать заказ', callback_data='neworder')]])

async def geolocate_point_start():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Определить место положение 🌐', request_location=True), ]],
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

