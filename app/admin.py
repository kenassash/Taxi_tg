import json
import os
import re
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command, Filter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from apscheduler.jobstores.base import JobLookupError, ConflictingIdError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.change_price import Settings
from app.database.requests import add_car, get_all_car, remove_car, print_all_online_executions, \
    get_all_drivers_with_update_date, get_users, get_one_car, get_driver_info, reset_to_zero, update_car, \
    get_users_count, add_change_price, ban_user, get_ban_all_user, get_cities_routes_price, \
    get_cities_routes_price_update, no_active, get_all_orders, city_routers_update_all, save_free_ride_by_phone, \
    update_driver, get_settings, update_settings

import app.keyboards as kb
import app.kb.kb_admin as kb_admin
from app.dialog import start_menu_dialog, start_menu_order
from filters.chat_type import ChatTypeFilter, IsAdmin
from handlers.handlers import router
from middleware.time_restriction_middleware import TimeRestrictionMiddleware

time_restriction_middleware_instance = TimeRestrictionMiddleware()

router.message.middleware(time_restriction_middleware_instance)
start_menu_dialog.callback_query.middleware(time_restriction_middleware_instance)
start_menu_order.callback_query.middleware(time_restriction_middleware_instance)

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
    await message.answer("Что хотите сделать?", reply_markup=kb_admin.admin_keyboard())


# ------------------информация о заказе---------

class InfoOrder(StatesGroup):
    info_order = State()


@admin.callback_query(IsAdmin(), F.data == 'info_order')
async def info_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.set_state(InfoOrder.info_order)
    await callback.message.answer('Отправьте номер заказа',
                                  reply_markup=await kb.cancel_order())


@admin.message(IsAdmin(), InfoOrder.info_order, F.text)
async def send_info_order(message: Message, state: FSMContext):
    input_int = message.text.strip()
    pattern = r"^\d+$"
    if re.match(pattern, input_int):
        await state.update_data(info_order=input_int)
        data = await state.get_data()
        order = await get_all_orders(data['info_order'])
        # await message.answer(f'{order.price}\n{order.user_rel.tg_id}')
        if order is not None:
            text_driver = (f"🔥Заказ <b>{order.id}</b>🔥\n\n"
                           f"📞Телефон <b>{order.user_rel.phone}</b>\n\n"
                           f"📍:<b>{order.city1_id} - {order.address1_id.upper()}</b>\n\n"
                           f"📍:<b>{order.city2_id} - {order.address2_id.upper()}</b>\n\n")
            if order.add_address:
                text_driver += f"🔃<b>{order.add_address}</b>\n\n"
            if order.add_new_address1:
                text_driver += f"📍:<b>{order.add_new_address1} - {order.add_street_address1.upper()}</b>\n\n"
            if order.add_new_address2:
                text_driver += f"📍:<b>{order.add_new_address2} - {order.add_street_address2.upper()}</b>\n\n"
            text_driver += f"Цена: <b>{order.price}Р</b>"

            await message.answer(text_driver)

            await state.clear()
        else:
            await message.answer('Ошибка. Такого заказа нет. Введите существующий')
    else:
        await message.answer("Пожалуйста, введите только цифры.")


# ------------------запрет водителю/активация---------

@admin.callback_query(IsAdmin(), F.data == 'driver_block')
async def block_driver(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.answer('Выберите',
                                  reply_markup=await kb_admin.button_deactive())


@admin.callback_query(IsAdmin(), F.data.startswith('blockdrive_'))
async def driver_no_active(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    status = callback.data.split('_')[1]
    await state.update_data(block_driver=status)
    await callback.message.edit_text('Выберите водителя',
                                     reply_markup=await kb_admin.driver_no_active())


@admin.callback_query(IsAdmin(), F.data.startswith('noactive_'))
async def no_active_driver(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    data = await state.get_data()
    driver_id = callback.data.split('_')[1]
    if data['block_driver'] == 'YES':
        await no_active(driver_id, is_start=False)
        await callback.message.edit_text(f'Водитель заблокирован')
    elif data['block_driver'] == 'NO':
        await no_active(driver_id, is_start=True)
        await callback.message.edit_text(f'Водитель разблокирован')
    await state.clear()


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
            'телефон': re.compile(r'^Телефон\s+(\+7\d{10})$', re.IGNORECASE),
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
    change_price_city_routers = State()


@admin.callback_query(IsAdmin(), F.data == 'change_settings')
async def change_settings_callback1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.edit_text('Выберите где нужно поменять тариф 💵',
                                     reply_markup=await kb_admin.change_money())


@admin.callback_query(IsAdmin(), or_f(F.data == 'changerouters', F.data == 'changeoutside', \
                                      F.data == 'change_point_start_end'))
async def change_settings_callback2(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    if callback.data == 'changerouters':
        await callback.message.answer('Ведите сумму со знаком + или -\nНапример: +30 или -20',
                                      reply_markup=await kb.cancel_order())
        await state.set_state(ChangeMoney.change_price_city_routers)

    elif callback.data == 'changeoutside':
        await callback.message.answer('Выберите где нужно поменять тариф 💵',
                                      reply_markup=await kb_admin.change_mouney_outside())
    elif callback.data == 'change_point_start_end':
        # await callback.message.answer(f'Введите сумму на которую поменять, сейчас стоит {Settings.fix_price}')
        # await state.set_state(ChangeMoney.change_price)

        # Изменить ценну в связке
        await callback.message.answer('Выберите первую точку',
                                      reply_markup=await kb_admin.change_mouney_routes1())


# ---Изменить ценну в связке целиком во всех точках----
@admin.message(IsAdmin(), ChangeMoney.change_price_city_routers, F.text)
async def change_city_routers_all(message: Message, state: FSMContext):
    input_int = message.text.strip()
    pattern = r"^[+-]\d+$"
    if re.match(pattern, input_int):
        await state.update_data(price=message.text)
        data = await state.get_data()
        await city_routers_update_all(data['price'])
        await message.answer(f'Цена успешна обновлена во всех связках')
        await state.clear()
    else:
        await message.answer("Пожалуйста, введите цифры со знаком + или -")


# ---Изменить ценну в связке----
@admin.callback_query(IsAdmin(), F.data.startswith('chroute_'))
async def change_route_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    city1 = callback.data.split('_')[1]
    await state.update_data(city1=city1)
    await callback.message.edit_text('Выберите вторую точку',
                                     reply_markup=await kb_admin.change_mouney_routes2(city1))


@admin.callback_query(IsAdmin(), F.data.startswith('finroute_'))
async def change_route_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    city2 = callback.data.split('_')[1]
    await state.update_data(city2=city2)
    data = await state.get_data()
    price = await get_cities_routes_price(data['city1'], data['city2'])
    await callback.message.edit_text(f'{data["city1"]} - {data["city2"]}\n'
                                     f'Цена <b>{price}</b>\n\n'
                                     f'Ведите сумму на какую изменить',
                                     reply_markup=await kb.cancel_order())
    await state.set_state(ChangeMoney.change_price)


@admin.message(IsAdmin(), ChangeMoney.change_price, F.text)
async def change_settings_value(message: Message, state: FSMContext):
    input_int = message.text.strip()
    pattern = r"^\d+$"
    if re.match(pattern, input_int):
        await state.update_data(price=message.text)
        data = await state.get_data()
        await get_cities_routes_price_update(data['city1'], data['city2'], data['price'])
        await message.answer(f'Цена успешна добавлена ')
        await state.clear()
    else:
        await message.answer("Пожалуйста, введите только цифры.")


# ------------------------------------------
# @admin.message(IsAdmin(), ChangeMoney.change_price, F.text)
# async def change_settings_value(message: Message, state: FSMContext):
#     input_int = message.text.strip()
#     pattern = r"^\d+$"
#     if re.match(pattern, input_int):
#         await state.update_data(setting=message.text)
#         Settings.set_fix_price(int(message.text))
#         await message.answer(f'Цена успешна добавлена {Settings.fix_price}')
#         await state.clear()
#     else:
#         await message.answer("Пожалуйста, введите только цифры.")


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
        zero_price_orders_info = [
            {"start_point": order.city1_id, "end_point": order.city2_id}
            for order in driver_info.orders_reply if order.price == 0
        ]

        # Формируем текст сообщения с информацией о водителе
        message_text = (
            f"Информация о водителе:\n"
            f"Имя: <b>{driver_info.name}</b>\n"
            f"Автомобиль: <b>{driver_info.car_name} - {driver_info.number_car}</b>\n"
            f"Всего заказов: <b>{total_orders}</b>\n"
            f"Общий заработок: <b>{total_earnings} руб.</b>\n"
            f"-------------------------------\n"
        )
        message_text_point = (
            f''
        )

        # message_text_id = (
        #     f''
        # )

        # Добавляем информацию о заказах с нулевой стоимостью, если такие есть
        if zero_price_orders_count > 0:
            message_text += f"<b>Заказов с нулевой стоимостью: {zero_price_orders_count}</b>\n"
            # for info in zero_price_orders_info:
            #     message_text_point += f"Начальная точка: <b>{info['start_point']}</b>\nКонечная точка: <b>{info['end_point']}</b>\n\n"

        # Создаем словарь для хранения количества заказов по датам
        orders_by_date = {}
        sorted_orders = sorted(driver_info.orders_reply, key=lambda order: order.created)
        for order in sorted_orders:
            date = order.created.date()
            orders_by_date[date] = orders_by_date.get(date, 0) + 1
            # message_text_id += f'<code>{order.id}</code>, '

        # Добавляем информацию о количестве заказов по датам в текст сообщения
        for date, count in orders_by_date.items():
            message_text += f"{date}: -  <b>{count}</b> заказов\n"

        await callback.answer('')
        await callback.message.answer(message_text, reply_markup=await kb.reset_zero(driver_id))
        # if zero_price_orders_count > 0:
        #     await callback.message.answer(text=message_text_point)
        # if total_orders > 0 :
        #     await callback.message.answer(text=message_text_id)
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
        await callback.message.answer('Введите номер телефона кого нужно забанить в формате +79991115577',
                                      reply_markup=await kb.cancel_order())
        await state.update_data(banned=True)
    elif callback.data == 'ban_no':
        await callback.message.answer('Введите номер телефона кого нужно забанить в формате +79991115577',
                                      reply_markup=await kb.cancel_order())

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
    pattern = r"^\+7\d{10}$"
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


# автоматические изменение цены
@admin.callback_query(IsAdmin(), F.data == 'nightchange')
async def night_change_cb(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.answer('Действие 💤', reply_markup=await kb_admin.night_changekb())


@admin.callback_query(IsAdmin(), F.data == 'stop_test')
async def stop_task(callback: CallbackQuery, apscheduler: AsyncIOScheduler):
    job_id = f"send_message_{callback.from_user.id}"
    job = apscheduler.get_job(job_id)
    print("Текущие задачи после добавления:", apscheduler.get_jobs())
    if job:
        apscheduler.remove_job(job_id)
        await callback.answer("Задача успешно отключена!")
    else:
        await callback.answer("Нет активной задачи для отключения.")


@admin.callback_query(IsAdmin(), F.data.startswith('nightchangekb_'))
async def night_change_kb(callback: CallbackQuery, bot: Bot, apscheduler: AsyncIOScheduler):
    await callback.answer('')
    answer = callback.data.split('_')[1]

    if answer == 'YES':
        try:
            apscheduler.add_job(city_routers_update_all,
                                trigger='cron',
                                hour=00,
                                id=f"set_night_price_{callback.from_user.id}",
                                args=['+50'],
                                )
            apscheduler.add_job(city_routers_update_all,
                                trigger='cron',
                                hour=7,
                                id=f"set_day_price{callback.from_user.id}",
                                args=['-50'],
                                )
            await callback.message.answer(
                'Задача добавлена с 12 ночи до 7 - +50 рублей во всех связках\nЗадача добавлена с 7 утра до 12 - -50 рублей во всех связках')
        except ConflictingIdError:
            await callback.message.answer('Задача добавлена с 12 ночи до 7 часов цена повышена во всех связка на ***')
            print('Ошибка запуска apscheduler.add_job')

    elif answer == 'NO':
        job_id1 = f"set_night_price_{callback.from_user.id}"
        job_id2 = f"set_day_price{callback.from_user.id}"
        print("Текущие задачи после добавления:", apscheduler.get_jobs())
        try:
            apscheduler.remove_job(job_id1)
            apscheduler.remove_job(job_id2)
            await callback.message.answer("Задача успешно отключена!")
        except JobLookupError:
            await callback.message.answer("Задача успешно отключена!")
            print('Ошибка остановки apscheduler.add_job')


# Бесплатные поездки
class FreeOrder(StatesGroup):
    free_order_user = State()
    free_order_price = State()


@admin.callback_query(IsAdmin(), F.data == 'freeorder')
async def freeorder1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.answer('Действие 💤', reply_markup=await kb_admin.free_order_kb())


@admin.callback_query(IsAdmin(), F.data == 'chn_freeorder')
async def freeorder2(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.answer('Введите цифру бесплатной поездки',
                                  reply_markup=await kb.cancel_order())
    await state.set_state(FreeOrder.free_order_price)


@admin.message(IsAdmin(), FreeOrder.free_order_price, F.text)
async def change_settings_value(message: Message, state: FSMContext):
    input_int = message.text.strip()
    pattern = r"^\d+$"
    if re.match(pattern, input_int):
        await state.update_data(free_price=message.text)
        data = await state.get_data()
        await update_settings(free_price=int(data['free_price']))
        await message.answer(f'Цена успешна добавлена ')
        await state.clear()
    else:
        await message.answer("Пожалуйста, введите только цифры.")


@admin.callback_query(IsAdmin(), F.data == 'add_freeorder')
async def freeorder2(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.answer('Введите номер телефона кому предоставить бесплатную поездку\nПример: +79981662233',
                                  reply_markup=await kb.cancel_order())
    await state.set_state(FreeOrder.free_order_user)


@admin.message(IsAdmin(), FreeOrder.free_order_user, F.text)
async def freeorder3(message: Message, state: FSMContext, bot: Bot):
    input_int = message.text.strip()
    pattern = r"^\+7\d{10}$"
    if re.match(pattern, input_int):
        await state.update_data(phone=input_int, free_ride=0)
        data = await state.get_data()
        tg_id = await save_free_ride_by_phone(data['phone'], data['free_ride'])
        if tg_id:
            await bot.send_message(
                chat_id=tg_id,
                text=f'Поздравляем! Ваша следующая поездка будет бесплатной! 🎉',
                reply_markup=await kb.main()
            )
            await message.answer("Операция прошла успешно")
        else:
            await message.answer("Пользователь с таким номером телефона не найден.")
        await state.clear()
    else:
        await message.answer("Введите номер телефона  в формате +79991115577")


# Пополнить баланс водителя
class Add_balance(StatesGroup):
    add_balance = State()


@admin.callback_query(IsAdmin(), F.data == 'add_balance')
async def add_balance1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.answer('Выберите автомобиль',
                                  reply_markup=await kb_admin.add_balance())


@admin.callback_query(IsAdmin(), F.data.startswith('addbalance_'))
async def add_balance2(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer('')
    driver_id = int(callback.data.split('_')[1])  # Получаем идентификатор водителя из колбэка
    driver_info = await get_driver_info(driver_id)
    text_driver = (f"<b>Автомобиль: </b>{driver_info.car_name}, {driver_info.number_car}\n"
                   f"<b>Телефон: </b>{driver_info.phone}\n"
                   f"<b>Баланс</b> {driver_info.price}\n")
    await bot.send_photo(chat_id=callback.from_user.id,
                         photo=driver_info.photo_car,
                         caption=text_driver)
    await callback.message.answer('Введите cумму которую пополнить баланс у водителя',
                                  reply_markup=await kb.cancel_order())
    await state.update_data(driver_id=driver_info.tg_id)
    await state.set_state(Add_balance.add_balance)


@admin.message(IsAdmin(), Add_balance.add_balance, F.text)
async def add_balance3(message: Message, state: FSMContext, bot: Bot):
    input_int = message.text.strip()
    pattern = r"^\d+$"
    if re.match(pattern, input_int):
        await state.update_data(price=input_int)
        data = await state.get_data()
        await update_driver(data['driver_id'], price=int(data['price']))
        await message.answer(f"Баланс водителя пополнен на {data['price']}")
        await state.clear()
    else:
        await message.answer("Пожалуйста, введите только цифры.")


@admin.callback_query(IsAdmin(), F.data == "auto_distribution")
async def change_settings(callback: CallbackQuery):
    status = await get_settings()
    if status.auto_distribution:
        await callback.message.edit_text(
            text=f"{callback.message.text.splitlines()[0]}\n\n"
                 f"Автораспределение: Выключено",
            reply_markup=kb_admin.admin_keyboard()
        )
        await update_settings(auto_distribution=False)
    else:
        await callback.message.edit_text(
            text=f"{callback.message.text.splitlines()[0]}\n\n"
                 f"Автораспределение: Включено",
            reply_markup=kb_admin.admin_keyboard(auto_distribution=True)
        )
        await update_settings(auto_distribution=True)


@admin.callback_query(IsAdmin(), F.data == "free_ride")
async def change_settings(callback: CallbackQuery):
    status = await get_settings()
    if status.free_ride:
        await callback.message.edit_text(
            text=f"{callback.message.text.splitlines()[0]}\n\n"
                 f"Бесплатная поездка: Выключено",
            reply_markup=kb_admin.admin_keyboard(free_ride=False)
        )
        await update_settings(free_ride=False)
    else:
        await callback.message.edit_text(
            text=f"{callback.message.text.splitlines()[0]}\n\n"
                 f"Бесплатная поездка: Включено",
            reply_markup=kb_admin.admin_keyboard(free_ride=True)
        )
        await update_settings(free_ride=True)
