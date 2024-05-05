import os
from datetime import timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.change_price import Settings
from app.database.requests import add_car, get_all_car, remove_car, print_all_online_executions, \
    get_all_drivers_with_update_date, get_users

import app.keyboards as kb
from filters.chat_type import ChatTypeFilter, IsAdmin

admin = Router()
admin.message.filter(ChatTypeFilter(["private"]), IsAdmin())


class AddDriver(StatesGroup):
    phone = State()
    car_name = State()
    number_car = State()
    photo_car = State()
    tg_id = State()


# class AdminProtect(Filter):
#     async def __call__(self, message: Message):
#         return message.from_user.id in [216159472]


@admin.message(IsAdmin(), Command("admin"))
async def admin_features(message: Message):
    # test = await get_info_online_tablo()
    # for i in test:
    #     await message.answer(i)
    await message.answer("Что хотите сделать?", reply_markup=await kb.admin_keyboard())


# ------------------Добавить машину /add_car-----------------------

@admin.callback_query(IsAdmin(), F.data == 'add_car')
async def add_phone1(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddDriver.phone)
    await callback.answer('')
    await callback.message.answer('Отправь номер телефона', reply_markup=await kb.cancel_order())


@admin.message(IsAdmin(), AddDriver.phone, F.text)
async def add_car_name(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(AddDriver.car_name)
    await message.answer('Введите название марки машины', reply_markup=await kb.cancel_order())


@admin.message(AddDriver.phone)
async def add_phone2(message: Message, state: FSMContext):
    await message.answer('Отправь телефон через кнопку')


@admin.message(IsAdmin(), AddDriver.car_name, F.text)
async def add_number_car(message: Message, state: FSMContext):
    await state.update_data(car_name=message.text)
    await state.set_state(AddDriver.number_car)
    await message.answer('Введите гос номер машины', reply_markup=await kb.cancel_order())


@admin.message(AddDriver.car_name)
async def add_car_name(message: Message, state: FSMContext):
    await message.answer('Введите коррекно название машины')


@admin.message(IsAdmin(), AddDriver.number_car, F.text)
async def add_item_category(message: Message, state: FSMContext):
    await state.update_data(number_car=message.text)
    await state.set_state(AddDriver.tg_id)
    await message.answer('Отправь CHAT-ID пользователя', reply_markup=await kb.cancel_order())


@admin.message(AddDriver.number_car)
async def add_number_car(message: Message, state: FSMContext):
    await message.answer('Отправь коррекно гос номер')


@admin.message(IsAdmin(), AddDriver.tg_id, F.text)
async def add_tg_id(message: Message, state: FSMContext):
    await state.update_data(tg_id=message.text)
    await state.set_state(AddDriver.photo_car)
    await message.answer('Отправь фото машины', reply_markup=await kb.cancel_order())


@admin.message(AddDriver.tg_id)
async def add_tg_id(message: Message, state: FSMContext):
    await message.answer('Отправь корректно chat-id')


@admin.message(IsAdmin(), AddDriver.photo_car, F.photo)
async def add_item_category(message: Message, state: FSMContext):
    await state.update_data(photo_car=message.photo[-1].file_id)
    data = await state.get_data()
    await message.answer_photo(photo=data['photo_car'], caption=f"Телефон {data['phone']}")
    await add_car(data)
    await message.answer('Машина успешна добавлена')
    await state.clear()


@admin.message(AddDriver.photo_car)
async def phone(message: Message, state: FSMContext):
    await message.answer('Отправь фото корректно')


# ------------------Удалить машину /delete_car-----------------------
@admin.callback_query(IsAdmin(), F.data == 'delete_car')
async def delete_car_message(callback: CallbackQuery):
    await callback.answer('')
    drivers = await get_all_car()
    for driver in drivers:
        await callback.message.answer_photo(photo=driver.photo_car)
        await callback.message.answer(f"{driver.phone}\n{driver.car_name}\n{driver.number_car}\n",
                                      reply_markup=await kb.delete_car(driver.id))


# ------------------Удалить машину /delete_car-----------------------
@admin.callback_query(IsAdmin(), F.data.startswith('deletecar_'))
async def delete_car_callback(callback: CallbackQuery):
    await callback.answer('')
    await remove_car(callback.data.split('_')[1])
    print(callback.data.split('_')[1])
    await callback.message.edit_text('Машина успешно удалена')


# ------------------вывод таблицы онлайн-----------------------
@admin.callback_query(IsAdmin(), F.data == 'online')
async def admin_features(callback: CallbackQuery):
    await callback.answer('')
    all_drivers = await get_all_drivers_with_update_date()

    active_drivers = [driver for driver in all_drivers if driver.active]
    inactive_drivers = [driver for driver in all_drivers if not driver.active]

    for driver in active_drivers:
        await callback.message.answer(f'Активные водители:\n'
                                      f'{driver.car_name}{driver.number_car} Дата обновления {driver.updated + timedelta(hours=9)}')

    for driver in inactive_drivers:
        await callback.message.answer(f'Неактивные водители:\n'
                                      f'{driver.car_name}{driver.number_car} Дата обновления {driver.updated + timedelta(hours=9)}')

    online_executions = await print_all_online_executions()
    for online_execution in online_executions:
        driver = online_execution
        for order in driver.orders_reply:
            # Выводим информацию о каждом водителе, связанном с этим заказом
            await callback.message.answer(f'Водитель машины -{driver.car_name} {driver.number_car}\n'
                                          f'Выполняет заказ №{order.id}\n'
                                          f"Начальная точка:{order.point_start}\n"
                                          f"Конечная точка: {order.point_end}\n"
                                          f"Расстояние:{order.distance}км\n"
                                          f"Время пути:{order.time_way}мин\n"
                                          f"Цена: {order.price}")

#--------------рассылка сообщений всем пользователям-------------
class Newsletter(StatesGroup):
    message = State()
@admin.callback_query(IsAdmin(), F.data == 'newletter')
async def newsletter(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.set_state(Newsletter.message)
    await callback.message.answer('Отправьте сообщение, которовые вы хотите разослать всем пользователям')

@admin.message(IsAdmin(), Newsletter.message)
async def newsletter_message(message: Message, state: FSMContext):
    await message.answer('Подождите .. идет рассылка')
    for user in await get_users():
        try:
            await message.send_copy(chat_id=user.tg_id)
        except:
            pass
    await message.answer('Рассылка успешно завершена')
    await state.clear()


#----------Изменить цену поездки----------
@admin.callback_query(IsAdmin(), F.data == 'change_settings')
async def change_settings_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.set_state(ChangeSettings.setting)
    await callback.message.answer('Выберите настройку, которую вы хотите изменить:',
                                  reply_markup=await kb.admin_change_price())


class ChangeSettings(StatesGroup):
    setting = State()
    change_price = State()


@admin.callback_query(IsAdmin(), F.data == 'distance_rate')
async def set_distance_rate(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.update_data(change_price='distance_rate')
    await state.set_state(ChangeSettings.setting)
    await callback.message.answer('Введите новую цену за километр:\n'
                                  'По умолчанию цена 40 за километр')


@admin.callback_query(IsAdmin(), F.data == 'time_rate')
async def set_time_rate(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.update_data(change_price='time_rate')
    await state.set_state(ChangeSettings.setting)
    await callback.message.answer(f'Введите новую цену за минуту:\n'
                                  f'По умолчанию цена 10 за минуту')


@admin.message(IsAdmin(), ChangeSettings.setting, F.text)
async def change_settings_value(message: Message, state: FSMContext):
    await state.update_data(setting=message.text)
    data = await state.get_data()
    print(str(data))
    change_price = data.get('change_price')
    if change_price == 'distance_rate':
        Settings.set_distance_rate(int(message.text))
        await message.answer(f'Цена за километр успешно изменена{Settings.distance_rate}')
    elif change_price == 'time_rate':
        Settings.set_time_rate(int(message.text))
        await message.answer(f'Цена за минуту успешно изменена {Settings.time_rate}')
    await state.clear()