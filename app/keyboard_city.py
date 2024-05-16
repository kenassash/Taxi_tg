from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

cities = {
    "Екатеринославка": 150,
    "Таёжный": 200,
    "Полигон": 350,
    "Восточный за ж/д": 200,
    "Агрохолдинг": 300,
    # "Другой населенный пункт (список)": '',
}
another_locality = {
    "Анновка"
}


async def keyboard_city1():
    keyboard = InlineKeyboardBuilder()
    for city, price in cities.items():
        keyboard.add(InlineKeyboardButton(text=city,
                                          callback_data=f'cities1_{city}_{price}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()

async def keyboard_city2():
    keyboard = InlineKeyboardBuilder()
    for city, price in cities.items():
        keyboard.add(InlineKeyboardButton(text=city,
                                          callback_data=f'cities2_{city}_{price}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data=f'backbutton_'))
    return keyboard.adjust(2).as_markup()

