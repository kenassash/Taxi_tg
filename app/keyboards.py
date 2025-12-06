from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.database.requests import get_all_car


async def main():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='🚕СОЗДАТЬ ЗАКАЗ🚕', callback_data='neworder'))
    return keyboard.adjust().as_markup()




async def order_now():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data=f'backbutton_'))
    keyboard.add(InlineKeyboardButton(text='Отменить заказ', callback_data=f'cancelorder_'))
    # keyboard.add(InlineKeyboardButton(text='Написать менеджеру', callback_data='manadger'))
    keyboard.add(InlineKeyboardButton(text='Заказать', callback_data='order_now'))
    return keyboard.adjust(2, 1, 1).as_markup()


async def admin_change_price():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Цена за километр', callback_data='distance_rate'))
    keyboard.add(InlineKeyboardButton(text='Цена за минуту', callback_data='time_rate'))
    keyboard.add(InlineKeyboardButton(text='Изменить ценну', callback_data='fix_price'))
    return keyboard.adjust(2).as_markup()


async def geolocate_point_start():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Определить место положение 🌐', request_location=True), ],
            [KeyboardButton(text='Отменить'), ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


async def phone():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Отправь номер телефона ☎️', request_contact=True), ],
            [KeyboardButton(text='Отменить'), ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    return keyboard


async def accept(order_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Принять заказ', callback_data=f'accept_{order_id}'))
    return keyboard.adjust().as_markup()

async def accept_or_skip(order_id: int) -> InlineKeyboardMarkup:
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text='Принять заказ',
            callback_data=f'accept_{order_id}'
        )
        keyboard.button(
            text="Пропустить",
            callback_data=f"skip_{order_id}"
        )
        return keyboard.as_markup()


async def close_and_finish(order_id, messege_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Завершить ✅', callback_data=f'finish_{order_id}_{messege_id}'))
    # keyboard.add(InlineKeyboardButton(text='Отказаться ❌', callback_data=f'close_{order_id}'))
    return keyboard.adjust(2).as_markup()


async def on_the_spot_kb(order_id, message_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='На месте 🎯', callback_data=f'onthespot_{order_id}_{message_id}'))
    keyboard.add(InlineKeyboardButton(text='Отказаться 🤦‍♂️', callback_data=f'close_{order_id}_{message_id}'))
    # keyboard.add(InlineKeyboardButton(text='Отменить заказ ❌', callback_data=f'deleteorder_{order_id}_{message_id}'))
    keyboard.add(InlineKeyboardButton(text='Завершить ✅', callback_data=f'finish_{order_id}_{message_id}'))
    return keyboard.adjust(1, 1, 1).as_markup()


async def time_wait(order_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='3 мин.', callback_data=f'timewait_{order_id}_3'))
    keyboard.add(InlineKeyboardButton(text='5 мин.', callback_data=f'timewait_{order_id}_5'))
    keyboard.add(InlineKeyboardButton(text='8 мин.', callback_data=f'timewait_{order_id}_8'))
    keyboard.add(InlineKeyboardButton(text='10 мин.', callback_data=f'timewait_{order_id}_10'))
    keyboard.add(InlineKeyboardButton(text='12 мин.', callback_data=f'timewait_{order_id}_12'))
    keyboard.add(InlineKeyboardButton(text='15 мин.', callback_data=f'timewait_{order_id}_15'))
    keyboard.add(InlineKeyboardButton(text='18 мин.', callback_data=f'timewait_{order_id}_18'))
    keyboard.add(InlineKeyboardButton(text='22 мин.', callback_data=f'timewait_{order_id}_22'))
    keyboard.add(InlineKeyboardButton(text='На месте 🎯', callback_data=f'onthespot_{order_id}'))
    keyboard.add(InlineKeyboardButton(text='Отказаться 🤦‍♂️', callback_data=f'close_{order_id}'))
    keyboard.add(InlineKeyboardButton(text='Завершить ✅', callback_data=f'finish_{order_id}'))

    return keyboard.adjust(4, 4, 1, 1, 1).as_markup()


async def back_button():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data=f'backbutton_'))
    keyboard.add(InlineKeyboardButton(text='Отменить заказ', callback_data=f'cancelorder_'))
    # keyboard.add(InlineKeyboardButton(text='Написать менеджеру', callback_data='manadger'))
    return keyboard.adjust(2).as_markup()


async def driver_start_or_finish():
    keyboard = InlineKeyboardBuilder()
    # keyboard.add(InlineKeyboardButton(text='Выйти на линию', callback_data=f'driverstart_'))
    # keyboard.add(InlineKeyboardButton(text='Уйти с линии', callback_data=f'driverfinish_'))
    keyboard.add(InlineKeyboardButton(text='Создать заказ 🏎️', callback_data='neworder'))

    return keyboard.adjust(2).as_markup()


async def go_to_order():
    keyboard = InlineKeyboardBuilder()
    url_group = 'https://t.me/Taxi_gorodok_bot'
    keyboard.add(InlineKeyboardButton(text='Перейти к заказу', url=url_group))
    return keyboard.adjust().as_markup()


async def reset_zero(driver_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Обнулить', callback_data=f'resetzero_{driver_id}'))
    return keyboard.adjust().as_markup()


async def cancel_order():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust().as_markup()


async def delete_order(order_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='❌ Отменить заказ',
                                      callback_data=f'deleteorder_{order_id}'))
    return keyboard.adjust().as_markup()


async def up_price(order_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='⬆️ Ускорить на 20р',
                                      callback_data=f'upprice_{order_id}'))
    keyboard.add(InlineKeyboardButton(text='❌ Отменить заказ',
                                      callback_data=f'deleteorder_{order_id}'))
    return keyboard.adjust(1, 1).as_markup()


async def add_car_or_no(id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Принять', callback_data=f'addcaradmin_{id}_YES'))
    keyboard.add(InlineKeyboardButton(text='Отказаться', callback_data=f'addcaradmin_{id}_NO'))
    return keyboard.adjust().as_markup()
