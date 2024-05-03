from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

main = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Создать заказ 🏎️', callback_data='neworder')]])

async def admin_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Добавить автомобиль', callback_data='add_car'))
    keyboard.add(InlineKeyboardButton(text='Удалить автомобиль', callback_data='delete_car'))
    keyboard.add(InlineKeyboardButton(text='Онлайн табло', callback_data='online'))
    keyboard.add(InlineKeyboardButton(text='Рассылка пользователям', callback_data='newletter'))
    keyboard.add(InlineKeyboardButton(text='Поменять тариф', callback_data='change_settings'))
    return keyboard.adjust(2).as_markup()

async def admin_change_price():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Цена за километр', callback_data='distance_rate'))
    keyboard.add(InlineKeyboardButton(text='Цена за минуту', callback_data='time_rate'))
    return keyboard.adjust(2).as_markup()
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

async def driver_start_or_finish():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Выйти на линию', callback_data=f'driverstart_'))
    keyboard.add(InlineKeyboardButton(text='Уйти с линии', callback_data=f'driverfinish_'))
    keyboard.add(InlineKeyboardButton(text='Создать заказ', callback_data='neworder'))
    return keyboard.adjust(2).as_markup()

async def delete_car(id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Удалить машину', callback_data=f'deletecar_{id}'))
    return keyboard.adjust().as_markup()


