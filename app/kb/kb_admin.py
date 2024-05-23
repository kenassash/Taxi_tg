from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.database.requests import get_all_car, get_cities_inside, get_cities_outside


async def admin_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Автомобили', callback_data='car_menu'))
    keyboard.add(InlineKeyboardButton(text='Информация', callback_data='info'))
    keyboard.add(InlineKeyboardButton(text='Рассылка пользователям', callback_data='newletter'))
    keyboard.add(InlineKeyboardButton(text='Поменять цену', callback_data='change_settings'))
    keyboard.add(InlineKeyboardButton(text='Пользователи', callback_data='number_passeger'))
    keyboard.add(InlineKeyboardButton(text='Бан', callback_data='ban_user'))
    keyboard.add(InlineKeyboardButton(text='На линии', callback_data='online'))
    return keyboard.adjust(2).as_markup()

async def car_menu_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Добавить', callback_data='add_car'))
    keyboard.add(InlineKeyboardButton(text='Изменить', callback_data='edit_car'))
    keyboard.add(InlineKeyboardButton(text='Удалить', callback_data='delete_car'))
    return keyboard.adjust(3).as_markup()

async def edit_car():
    drivers = await get_all_car()
    keyboard = InlineKeyboardBuilder()
    for driver in drivers:
        keyboard.add(InlineKeyboardButton(text=f'{driver.name} - {driver.number_car}',
                                          callback_data=f'editcar_{driver.id}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust().as_markup()

async def delete_car():
    drivers = await get_all_car()
    keyboard = InlineKeyboardBuilder()
    for driver in drivers:
        keyboard.add(InlineKeyboardButton(text=f'{driver.name} - {driver.number_car}',
                                          callback_data=f'deletecar_{driver.id}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust().as_markup()


async def all_car():
    drivers = await get_all_car()
    keyboard = InlineKeyboardBuilder()
    for driver in drivers:
        keyboard.add(InlineKeyboardButton(text=f'{driver.name} - {driver.number_car}',
                                          callback_data=f'infocardriver_{driver.id}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()

async def change_money():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text=f'Местно', callback_data=f'changeinside'))
    keyboard.add(InlineKeyboardButton(text='Другой нп', callback_data=f'changeoutside'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()

async def change_mouney_inside():
    keyboard = InlineKeyboardBuilder()
    cities = await get_cities_inside()
    for city in cities:
        keyboard.add(InlineKeyboardButton(text=city.city_name,
                                          callback_data=f'chin_{city.city_name}_{city.price}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()

async def change_mouney_outside():
    keyboard = InlineKeyboardBuilder()
    cities = await get_cities_outside()
    for city in cities:
        keyboard.add(InlineKeyboardButton(text=city.city_name,
                                          callback_data=f'chout_{city.city_name}_{city.price}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()

async def ban_users_phone():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Забанить', callback_data=f'ban_add'))
    keyboard.add(InlineKeyboardButton(text='Разбанить', callback_data=f'ban_no'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()




