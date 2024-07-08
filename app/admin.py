import json
import os
import re
from datetime import timedelta, time

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command, Filter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.change_price import Settings
from app.database.requests import add_car, get_all_car, remove_car, print_all_online_executions, \
    get_all_drivers_with_update_date, get_users, get_one_car, get_driver_info, reset_to_zero, update_car, \
    get_users_count, add_change_price, ban_user, get_ban_all_user

import app.keyboards as kb
import app.kb.kb_admin as kb_admin
from filters.chat_type import ChatTypeFilter, IsAdmin
from handlers.handlers import router
from middleware.time_restriction_middleware import TimeRestrictionMiddleware

time_restriction_middleware_instance = router.message.middleware(TimeRestrictionMiddleware())

admin = Router()
admin.message.filter(ChatTypeFilter(["private"]), IsAdmin())


class AddDriver(StatesGroup):
    name = State()
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
    await message.answer("Что хотите сделать?", reply_markup=await kb_admin.admin_keyboard())


# -----------------Время сна---------------

@admin.callback_query(IsAdmin(), F.data == 'time_restriction')
async def time_restriction(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.answer('Действие 💤', reply_markup=await kb_admin.turn_time_rest())


@admin.callback_query(IsAdmin(), F.data.startswith('turntimerest_'))
async def turn_or_of_timerest(callback: CallbackQuery):
    await callback.answer('')
    answer = callback.data.split('_')[1]

    if answer == 'YES':
        time_restriction_middleware_instance.activate()
        await callback.message.answer("Ограничение времени отправки сообщений активировано.")
    elif answer == 'NO':
        time_restriction_middleware_instance.deactivate()
        await callback.message.answer("Ограничение времени отправки сообщений деактивировано.")


# ------------------Меню машин-----------------------
@admin.callback_query(IsAdmin(), F.data == 'car_menu')
async def car_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.edit_text('Управление автомобилями 🚗',
                                     reply_markup=await kb_admin.car_menu_keyboard())


# ------------------Добавить машину /add_car-----------------------

@admin.callback_query(IsAdmin(), F.data == 'add_car')
async def add_phone1(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddDriver.phone)
    await callback.answer('')
    await callback.message.answer('Отправь номер телефона через 7', reply_markup=await kb.cancel_order())


@admin.message(IsAdmin(), AddDriver.phone, F.text)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(AddDriver.name)
    await message.answer('Как зовут водителя', reply_markup=await kb.cancel_order())


@admin.message(AddDriver.phone)
async def add_phone2(message: Message, state: FSMContext):
    await message.answer('Отправь телефон через кнопку')


@admin.message(IsAdmin(), AddDriver.name, F.text)
async def add_car_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddDriver.car_name)
    await message.answer('Введите название марки машины', reply_markup=await kb.cancel_order())


@admin.message(AddDriver.name)
async def add_name2(message: Message, state: FSMContext):
    await message.answer('Отправь имя водителя')


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

# drivers = await get_all_car()
# for driver in drivers:
#     await callback.message.answer_photo(photo=driver.photo_car)
#     await callback.message.answer(f"{driver.phone}\n{driver.name}\n{driver.car_name}\n{driver.number_car}\n",
#                                   reply_markup=await kb_admin.delete_car(driver.id))


# ------------------Удалить машину /delete_car-----------------------
class EditCarStates(StatesGroup):
    waiting_for_new_value = State()


@admin.callback_query(IsAdmin(), F.data == 'edit_car')
async def edit_car(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.answer('Выберите какую машину изменить 🕵️‍♀️',
                                  reply_markup=await kb_admin.edit_car())


@admin.callback_query(IsAdmin(), F.data.startswith('editcar_'))
async def edit_car_1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    driver = await get_one_car(callback.data.split('_')[1])
    await callback.message.answer_photo(photo=driver.photo_car)
    await callback.message.answer(f"Телефон - {driver.phone}\n"
                                  f"Имя - {driver.name}\n"
                                  f"Название - {driver.car_name}\n"
                                  f"Номер - {driver.number_car}\n")
    await state.update_data(driver_id=driver.id)
    await callback.message.answer(f'Введите что хотите изменить\n'
                                  f'Например: Номер M404BH\n'
                                  f'Или: Фото и после пришлите фото',
                                  reply_markup=await kb.cancel_order())
    await state.set_state(EditCarStates.waiting_for_new_value)


@admin.message(IsAdmin(), EditCarStates.waiting_for_new_value, (F.text | F.photo))
async def edit_car_2(message: Message, state: FSMContext):
    if message.text:
        new_value = message.text
        data = await state.get_data()
        patterns = {
            'имя': re.compile(r'^Имя\s+(.+)$', re.IGNORECASE),
            'телефон': re.compile(r'^Телефон\s+([7]\d{10})$', re.IGNORECASE),
            'название': re.compile(r'^Название\s+(.+)$', re.IGNORECASE),
            'номер': re.compile(r'^Номер\s+(.+)$', re.IGNORECASE),
        }
        matched = False
        for field, pattern in patterns.items():
            match = pattern.match(new_value)
            if match:
                new_value_text = match.group(1)
                if field == 'телефон':
                    await state.update_data(phone=new_value_text)
                    await message.answer(f"Телефон изменен на: {new_value_text}")
                elif field == 'имя':
                    await state.update_data(name=new_value_text)
                    await message.answer(f"Имя изменено на: {new_value_text}")
                elif field == 'название':
                    await state.update_data(car_name=new_value_text)
                    await message.answer(f"Название изменено на: {new_value_text}")
                elif field == 'номер':
                    await state.update_data(number_car=new_value_text)
                    await message.answer(f"Номер изменен на: {new_value_text}")
                matched = True
                break
        if not matched:
            await message.answer(f"Не верно ввели атрибут. Пожалуйста, попробуйте еще раз.")
            return

    elif message.photo:
        photo = message.photo[-1]  # Получаем фото с максимальным разрешением
        file_id = photo.file_id
        await state.update_data(photo_car=file_id)
        await message.answer("Фото изменено.")
    data = await state.get_data()

    await update_car(data)
    await state.clear()
    return


@admin.callback_query(IsAdmin(), F.data == 'number_passeger')
async def number_passeger(callback_query: CallbackQuery):
    await callback_query.answer('')
    users = await get_users_count()
    await callback_query.message.edit_text(f'Всего пользователей {users} 🥳')


@admin.callback_query(IsAdmin(), F.data == 'delete_car')
async def delete_car_message(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.answer('Выберите машину какую удалить 🥲',
                                  reply_markup=await kb_admin.delete_car())


@admin.callback_query(IsAdmin(), F.data.startswith('deletecar_'))
async def delete_car_callback(callback: CallbackQuery):
    await callback.answer('')
    await remove_car(callback.data.split('_')[1])
    await callback.message.edit_text('Машина удалена')


# ------------------вывод таблицы онлайн-----------------------
@admin.callback_query(IsAdmin(), F.data == 'online')
async def admin_features(callback: CallbackQuery):
    await callback.answer('')
    all_drivers = await get_all_drivers_with_update_date()

    active_drivers = [driver for driver in all_drivers if driver.active]
    inactive_drivers = [driver for driver in all_drivers if not driver.active]

    for driver in active_drivers:
        await callback.message.answer(f'Активные водители:\n'
                                      f'Машина {driver.car_name} - {driver.number_car} Дата обновления {driver.updated + timedelta(hours=9)}')

    for driver in inactive_drivers:
        await callback.message.answer(f'Неактивные водители:\n'
                                      f'Машина {driver.car_name} - {driver.number_car} Дата обновления {driver.updated + timedelta(hours=9)}')

    # online_executions = await print_all_online_executions()
    # for online_execution in online_executions:
    #     driver = online_execution
    #     for order in driver.orders_reply:
    #         # Выводим информацию о каждом водителе, связанном с этим заказом
    #         await callback.message.answer(f'Водитель машины -{driver.car_name} {driver.number_car}\n'
    #                                       f'Выполняет заказ №{order.id}\n'
    #                                       f"Начальная точка:{order.point_start}\n"
    #                                       f"Конечная точка: {order.point_end}\n"
    #                                       f"Расстояние:{order.distance}км\n"
    #                                       f"Время пути:{order.time_way}мин\n"
    #                                       f"Цена: {order.price}")


# --------------рассылка сообщений всем пользователям-------------
class Newsletter(StatesGroup):
    message = State()


@admin.callback_query(IsAdmin(), F.data == 'newletter')
async def newsletter(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.set_state(Newsletter.message)
    await callback.message.answer('Отправьте сообщение, которовые вы хотите разослать всем пользователям',
                                  reply_markup=await kb.cancel_order())


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


# ----------Изменить цену поездки----------

class ChangeMoney(StatesGroup):
    price = State()
    change_price = State()


@admin.callback_query(IsAdmin(), F.data == 'change_settings')
async def change_settings_callback1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.edit_text('Выберите где нужно поменять тариф 💵',
                                     reply_markup=await kb_admin.change_money())


@admin.callback_query(IsAdmin(), or_f(F.data == 'changeinside', F.data == 'changeoutside', \
                                      F.data == 'change_point_start_end'))
async def change_settings_callback2(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    if callback.data == 'changeinside':
        await callback.message.answer('Выберите где нужно поменять тариф 💵',
                                      reply_markup=await kb_admin.change_mouney_inside())
    elif callback.data == 'changeoutside':
        await callback.message.answer('Выберите где нужно поменять тариф 💵',
                                      reply_markup=await kb_admin.change_mouney_outside())
    elif callback.data == 'change_point_start_end':
        await callback.message.answer(f'Введите сумму на которую поменять, сейчас стоит {Settings.fix_price}')
        await state.set_state(ChangeMoney.change_price)

@admin.message(IsAdmin(), ChangeMoney.change_price, F.text)
async def change_settings_value(message: Message, state: FSMContext):
    input_int = message.text.strip()
    pattern = r"^\d+$"
    if re.match(pattern, input_int):
        await state.update_data(setting=message.text)
        Settings.set_fix_price(int(message.text))
        await message.answer(f'Цена успешна добавлена {Settings.fix_price}')
        await state.clear()
    else:
        await message.answer("Пожалуйста, введите только цифры.")


@admin.callback_query(IsAdmin(), or_f(F.data.startswith('chin_'), F.data.startswith('chout_')))
async def change_settings_callback3(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    if callback.data.startswith('chin_'):
        city = callback.data.split('_')[1]
        database = "inside"
        await state.update_data(city_name=city, database=database)
        price = callback.data.split('_')[2]
        await callback.message.edit_text(f'Вы выбрали {city}, цена: {price}р\n\n'
                                         f'Введите сумму на которую изменить')
    elif callback.data.startswith('chout_'):
        city = callback.data.split('_')[1]
        database = "outside"
        await state.update_data(city_name=city, database=database)
        price = callback.data.split('_')[2]
        await callback.message.edit_text(f'Вы выбрали {city}, цена: {price}р\n\n'
                                         f'Введите сумму на которую изменить')
    await state.set_state(ChangeMoney.price)


@admin.message(IsAdmin(), ChangeMoney.price, F.text)
async def change_settings_callback4(message: Message, state: FSMContext):
    input_int = message.text.strip()
    pattern = r"^\d+$"
    if re.match(pattern, input_int):
        await state.update_data(price=input_int)
        data = await state.get_data()
        await add_change_price(data['price'], data['city_name'], data['database'])
        await message.answer("Цена успешно обновилась")
        await state.clear()
    else:
        await message.answer("Пожалуйста, введите только цифры.")


# class ChangeSettings(StatesGroup):
#     setting = State()
#     change_price = State()

# @admin.callback_query(IsAdmin(), F.data == 'distance_rate')
# async def set_distance_rate(callback: CallbackQuery, state: FSMContext):
#     await callback.answer('')
#     await state.update_data(change_price='distance_rate')
#     await state.set_state(ChangeSettings.setting)
#     await callback.message.answer('Введите новую цену за километр:\n'
#                                   'По умолчанию цена 40 за километр', await kb.cancel_order())
#
#
# @admin.callback_query(IsAdmin(), F.data == 'time_rate')
# async def set_time_rate(callback: CallbackQuery, state: FSMContext):
#     await callback.answer('')
#     await state.update_data(change_price='time_rate')
#     await state.set_state(ChangeSettings.setting)
#     await callback.message.answer(f'Введите новую цену за минуту:\n'
#                                   f'По умолчанию цена 10 за минуту', await kb.cancel_order())
#
#
# @admin.message(IsAdmin(), ChangeSettings.setting, F.text)
# async def change_settings_value(message: Message, state: FSMContext):
#     await state.update_data(setting=message.text)
#     Settings.set_fix_price(int(message.text))
#     await message.answer(f'Цена успешна добавлена {Settings.fix_price}')

# change_price = data.get('change_price')
# if change_price == 'distance_rate':
#     Settings.set_distance_rate(int(message.text))
#     await message.answer(f'Цена за километр успешно изменена {Settings.distance_rate}')
# elif change_price == 'time_rate':
#     Settings.set_time_rate(int(message.text))
# #     await message.answer(f'Цена за минуту успешно изменена {Settings.time_rate}')
# await state.clear()

# Добавление машины от пользователя
@admin.callback_query(IsAdmin(), F.data.startswith('addcaradmin_'))
async def addcaradmin(callback: CallbackQuery, bot: Bot):
    await callback.answer('')
    answer = callback.data.split("_")[2]
    driver_id = callback.data.split("_")[1]
    driver_id = await get_one_car(driver_id)

    if answer == "YES":
        await callback.message.delete()
        await bot.send_message(chat_id=driver_id.tg_id,
                               text='Машина успешно добавлена')
    elif answer == "NO":
        await callback.message.delete()
        await bot.send_message(chat_id=driver_id.tg_id,
                               text='Извините, машина не добавлена')
        await remove_car(callback.data.split('_')[1])
    await bot.answer_callback_query(callback.id)


@admin.callback_query(IsAdmin(), F.data == 'info')
async def info(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.answer('Выберите автомобиль',
                                  reply_markup=await kb_admin.all_car())


@admin.callback_query(IsAdmin(), F.data.startswith('infocardriver_'))
async def info_car_driver(callback: CallbackQuery):
    driver_id = int(callback.data.split('_')[1])  # Получаем идентификатор водителя из колбэка
    driver_info = await get_driver_info(driver_id)

    if driver_info is not None:
        total_orders = len(driver_info.orders_reply)
        total_earnings = sum(order.price for order in driver_info.orders_reply)
        # data_created = [data.created for data in driver_info.orders_reply]
        # print(data_created)
        # Подсчитываем количество заказов с нулевой стоимостью
        zero_price_orders_count = sum(1 for order in driver_info.orders_reply if order.price == 0)


        # Формируем текст сообщения с информацией о водителе
        message_text = (
            f"Информация о водителе:\n"
            f"Имя: <b>{driver_info.name}</b>\n"
            f"Автомобиль: <b>{driver_info.car_name} - {driver_info.number_car}</b>\n"
            f"Всего заказов: <b>{total_orders}</b>\n"
            f"Общий заработок: <b>{total_earnings} руб.</b>\n"
            f"-------------------------------\n"
        )
        # Добавляем информацию о заказах с нулевой стоимостью, если такие есть
        if zero_price_orders_count > 0:
            message_text += f"<b>Заказов с нулевой стоимостью: {zero_price_orders_count}</b>\n"

        # Создаем словарь для хранения количества заказов по датам
        orders_by_date = {}
        for order in driver_info.orders_reply:
            date = order.created.date() + timedelta(hours=9)
            orders_by_date[date] = orders_by_date.get(date, 0) + 1

        # Добавляем информацию о количестве заказов по датам в текст сообщения
        for date, count in orders_by_date.items():
            message_text += f"{date}: -  <b>{count}</b> заказов\n"

        await callback.answer('')
        await callback.message.answer(message_text, reply_markup=await kb.reset_zero(driver_id))
    else:
        await callback.answer('Информация о водителе не найдена')


@admin.callback_query(IsAdmin(), F.data.startswith('resetzero_'))
async def reset_zero(callback: CallbackQuery):
    await callback.answer('')
    driver_id = callback.data.split('_')[1]
    await reset_to_zero(driver_id)
    await callback.message.edit_text('Информация обнулена')


class BanUser(StatesGroup):
    banned = State()


@admin.callback_query(IsAdmin(), F.data == 'ban_user')
async def ban_users(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.answer('Выберите действие ❌',
                                  reply_markup=await kb_admin.ban_users_phone())


@admin.callback_query(IsAdmin(), or_f(F.data == 'ban_add', F.data == 'ban_no', F.data == 'ban_list'))
async def ban_users2(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    if callback.data == 'ban_add':
        await callback.message.answer('Введите номер телефона кого нужно забанить в формате 79991115577\n'
                                      'Без знака плюс', reply_markup=await kb.cancel_order())
        await state.update_data(banned=True)
    elif callback.data == 'ban_no':
        await callback.message.answer('Введите номер телефона кого нужно забанить в формате 79991115577\n'
                                      'Без знака плюс', reply_markup=await kb.cancel_order())

        await state.update_data(banned=False)
    elif callback.data == 'ban_list':
        results = await get_ban_all_user()
        message_text = (
            f'Лист забаненных пользователей\n\n'
        )
        for result in results:
            message_text += f'{result.phone}\n'

        await callback.message.answer(message_text)
        return
    await state.set_state(BanUser.banned)


@admin.message(IsAdmin(), BanUser.banned, F.text)
async def ban_users3(message: Message, state: FSMContext):
    input_int = message.text.strip()
    pattern = r"^7\d{10}$"
    if re.match(pattern, input_int):
        await state.update_data(phone=input_int)
        data = await state.get_data()
        await ban_user(data['phone'], data['banned'])
        await message.answer("Операция прошла успешно")
        await state.clear()
    else:
        await message.answer("Введите номер телефона  в формате 79991115577")


# --- Отвтеить на  заявку  Администратору-----
class SendToUser(StatesGroup):
    sendTouser = State()


@admin.callback_query(IsAdmin(), F.data == 'sendTouser')
async def sendTouser(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.answer('Напишите ответ используя модулем "Ответить"')
    await state.set_state(SendToUser.sendTouser)


@admin.message(IsAdmin(), SendToUser.sendTouser, F.text)
async def send_user(message: Message, state: FSMContext, bot: Bot):
    if (message.reply_to_message):
        try:
            user_id = message.reply_to_message.text.split('"')[1]
            await bot.send_message(user_id, f'Ответ от менеджера:\n\n<b>{message.text}</b>')
            await message.answer('Сообщение отправлено')
            await state.clear()
        except IndexError:
            await message.reply(
                "Не удалось извлечь идентификатор пользователя. Пожалуйста, убедитесь, что вы отвечаете на правильное сообщение.")
            await state.clear()
    else:
        await message.answer('Используй кнопку ответить на сообщение')
        await state.set_state(SendToUser.sendTouser)
