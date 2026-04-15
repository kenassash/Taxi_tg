import json
import os
import re
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
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
    update_driver, get_settings, update_settings, adjust_user_free_ride_counters, get_driver, start_order_execution, \
    set_chat_id_driver, set_chat_id_user
from app.driver_activity_check import send_activity_check_to_drivers, check_driver_activity_responses

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


class SleepTime(StatesGroup):
    set_start_hour = State()
    set_start_minute = State()
    set_end_hour = State()
    set_end_minute = State()
    set_days = State()
    set_message = State()


class DriverActivity(StatesGroup):
    set_interval_hours = State()
    set_timeout_minutes = State()


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
    settings = await get_settings()
    if not settings or not settings.auto_distribution:
        await callback.message.answer('Автораспределение выключено — управление активностью водителей недоступно.')
        return

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
    driver_id_str = callback.data.split('_')[1]
    try:
        driver_id = int(driver_id_str)
    except ValueError:
        await callback.message.edit_text('Ошибка: неверный ID водителя')
        await state.clear()
        return
    
    if data['block_driver'] == 'YES':
        await no_active(driver_id, is_start=False)
        await callback.message.edit_text(f'Водитель заблокирован')
    elif data['block_driver'] == 'NO':
        await no_active(driver_id, is_start=True)
        await callback.message.edit_text(f'Водитель разблокирован')
    await state.clear()

# ------------------Активность водителей (интервалы)---------------


async def restart_driver_activity_jobs(bot: Bot, apscheduler: AsyncIOScheduler):
    """Перезапуск задач проверки активности с новыми настройками"""
    settings = await get_settings()
    interval_hours = settings.driver_check_interval_hours if settings and settings.driver_check_interval_hours else 2

    for job_id in ['driver_activity_check_send', 'driver_activity_check_responses']:
        try:
            apscheduler.remove_job(job_id)
        except JobLookupError:
            pass

    # Запускаем проверку каждую минуту, чтобы сообщения отправлялись точно через установленный интервал
    apscheduler.add_job(
        send_activity_check_to_drivers,
        trigger='interval',
        minutes=1,
        id='driver_activity_check_send',
        args=[bot],
        replace_existing=True
    )
    apscheduler.add_job(
        check_driver_activity_responses,
        trigger='interval',
        minutes=1,  # таймаут читается внутри функции
        id='driver_activity_check_responses',
        args=[bot],
        replace_existing=True
    )


@admin.callback_query(IsAdmin(), F.data == 'driver_activity')
async def driver_activity_menu(callback: CallbackQuery):
    await callback.answer('')
    settings = await get_settings()
    interval = settings.driver_check_interval_hours if settings and settings.driver_check_interval_hours else 2
    timeout = settings.driver_inactive_timeout_minutes if settings and settings.driver_inactive_timeout_minutes else 10
    text = (
        "<b>Активность водителей</b>\n\n"
        f"Текущий интервал отправки: {interval} ч\n"
        f"Текущий таймаут без ответа: {timeout} мин\n\n"
        "Выберите, что изменить:"
    )
    await callback.message.answer(text, reply_markup=await kb_admin.driver_activity_kb(), parse_mode='HTML')


@admin.callback_query(IsAdmin(), F.data == 'driver_activity_set_interval')
async def driver_activity_set_interval(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.answer("Введите интервал отправки (в часах, целое число > 0):", reply_markup=await kb.cancel_order())
    await state.set_state(DriverActivity.set_interval_hours)


@admin.callback_query(IsAdmin(), F.data == 'driver_activity_set_timeout')
async def driver_activity_set_timeout(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.answer("Введите таймаут без ответа (в минутах, целое число > 0):", reply_markup=await kb.cancel_order())
    await state.set_state(DriverActivity.set_timeout_minutes)


@admin.message(IsAdmin(), DriverActivity.set_interval_hours, F.text)
async def driver_activity_save_interval(message: Message, state: FSMContext, apscheduler: AsyncIOScheduler = None, bot: Bot | None = None):
    value = message.text.strip()
    if not value.isdigit() or int(value) <= 0:
        await message.answer("Введите положительное целое число (часы).")
        return
    hours = int(value)
    await update_settings(driver_check_interval_hours=hours)
    await message.answer(f"Интервал отправки установлен: {hours} ч")

    if apscheduler and bot:
        await restart_driver_activity_jobs(bot, apscheduler)
        await message.answer("Задачи проверки активности перезапущены с новым интервалом.")
    await state.clear()


@admin.message(IsAdmin(), DriverActivity.set_timeout_minutes, F.text)
async def driver_activity_save_timeout(message: Message, state: FSMContext, apscheduler: AsyncIOScheduler = None, bot: Bot | None = None):
    value = message.text.strip()
    if not value.isdigit() or int(value) <= 0:
        await message.answer("Введите положительное целое число (минуты).")
        return
    minutes = int(value)
    await update_settings(driver_inactive_timeout_minutes=minutes)
    await message.answer(f"Таймаут без ответа установлен: {minutes} мин")

    if apscheduler and bot:
        await restart_driver_activity_jobs(bot, apscheduler)
    await state.clear()


@admin.callback_query(IsAdmin(), F.data == 'admin_back')
async def admin_back(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.answer("Что хотите сделать?", reply_markup=kb_admin.admin_keyboard())


# ------------------Список водителей (активен/неактивен)---------

@admin.callback_query(IsAdmin(), F.data == 'drivers_list')
async def drivers_list(callback: CallbackQuery):
    await callback.answer('')
    settings = await get_settings()
    if not settings or not settings.auto_distribution:
        await callback.message.answer('Автораспределение выключено — просмотр статуса водителей недоступен.')
        return
    
    drivers_result = await get_all_car()
    drivers = list(drivers_result) if drivers_result else []
    
    if not drivers:
        await callback.message.answer('В системе нет водителей.')
        return
    
    # Формируем список: 1 строка = 1 водитель
    lines = ["📋 Список водителей\n"]
    
    active_count = 0
    inactive_count = 0
    
    for driver in drivers:
        status = "🟢" if driver.active else "🔴"
        driver_line = f"{status} {driver.name} - {driver.car_name} - {driver.number_car} - {driver.phone}"
        lines.append(driver_line)
        if driver.active:
            active_count += 1
        else:
            inactive_count += 1
    
    lines.append(f"\nВсего: {len(drivers)} (🟢 {active_count} | 🔴 {inactive_count})")
    text = "\n".join(lines)
    
    await callback.message.answer(text, parse_mode='HTML')


# -----------------Время сна---------------

@admin.callback_query(IsAdmin(), F.data == 'time_restriction')
async def time_restriction(callback: CallbackQuery):
    await callback.answer('')
    settings = await get_settings()
    sleep_manual_active = settings.sleep_manual_active if settings else False
    sleep_time_active = time_restriction_middleware_instance.active
    await callback.message.answer('Действие 💤', reply_markup=await kb_admin.turn_time_rest(sleep_manual_active, sleep_time_active))


@admin.callback_query(IsAdmin(), F.data.startswith('sleep_manual_'))
async def turn_sleep_manual(callback: CallbackQuery):
    """Включение/выключение мгновенного сна (без времени)"""
    await callback.answer('')
    action = callback.data.split('_')[2]
    
    if action == 'ON':
        await update_settings(sleep_manual_active=True)
        await callback.message.answer("✅ Мгновенный сон включен. Такси заблокировано сразу.")
    elif action == 'OFF':
        await update_settings(sleep_manual_active=False)
        await callback.message.answer("❌ Мгновенный сон выключен.")
    
    # Обновляем клавиатуру с новым статусом
    settings = await get_settings()
    sleep_manual_active = settings.sleep_manual_active if settings else False
    sleep_time_active = time_restriction_middleware_instance.active
    await callback.message.edit_reply_markup(reply_markup=await kb_admin.turn_time_rest(sleep_manual_active, sleep_time_active))


@admin.callback_query(IsAdmin(), F.data.startswith('turntimerest_'))
async def turn_or_of_timerest(callback: CallbackQuery):
    """Включение/выключение сна по времени"""
    await callback.answer('')
    answer = callback.data.split('_')[1]

    if answer == 'YES':
        time_restriction_middleware_instance.activate()
        await callback.message.answer("✅ Сон по времени включен.")
    elif answer == 'NO':
        time_restriction_middleware_instance.deactivate()
        await callback.message.answer("❌ Сон по времени выключен.")
    
    # Обновляем клавиатуру с новым статусом
    settings = await get_settings()
    sleep_manual_active = settings.sleep_manual_active if settings else False
    sleep_time_active = time_restriction_middleware_instance.active
    await callback.message.edit_reply_markup(reply_markup=await kb_admin.turn_time_rest(sleep_manual_active, sleep_time_active))


WEEKDAY_LABELS = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}


def format_sleep_days(days: list[int] | None) -> str:
    if not days:
        return "Все дни"
    sorted_days = sorted(days)
    return ", ".join(WEEKDAY_LABELS.get(day, str(day)) for day in sorted_days)


@admin.callback_query(IsAdmin(), F.data == 'sleep_time_set_time')
async def sleep_time_set_time(callback: CallbackQuery):
    """Открыть настройки времени сна"""
    await callback.answer('')
    settings = await get_settings()
    if not settings:
        await callback.message.answer('Ошибка: настройки не найдены')
        return
    
    start_hour = settings.sleep_start_hour if settings.sleep_start_hour is not None else 23
    start_minute = settings.sleep_start_minute if settings.sleep_start_minute is not None else 0
    end_hour = settings.sleep_end_hour if settings.sleep_end_hour is not None else 7
    end_minute = settings.sleep_end_minute if settings.sleep_end_minute is not None else 0
    days_text = format_sleep_days(settings.sleep_days)
    message_text = settings.sleep_message if settings.sleep_message else "(не задано)"
    
    print(f'Текущие настройки времени сна: начало {start_hour:02d}:{start_minute:02d}, окончание {end_hour:02d}:{end_minute:02d}')
    
    # Формируем информацию о рабочих и выходных днях
    if settings.sleep_days:
        # Рабочие дни - это дни, которые В списке sleep_days (такси работает, кроме времени сна)
        work_days_set = sorted(settings.sleep_days)
        work_days_text = ", ".join([WEEKDAY_LABELS[d] for d in work_days_set])
        
        # Выходные дни - это дни, которых НЕТ в списке sleep_days (такси закрыто весь день)
        all_days = set(range(7))
        weekend_days_set = sorted(all_days - set(settings.sleep_days))
        if weekend_days_set:
            weekend_days_text = ", ".join([WEEKDAY_LABELS[d] for d in weekend_days_set])
        else:
            weekend_days_text = "Нет выходных"
    else:
        work_days_text = "Все дни"
        weekend_days_text = "Нет выходных"
    
    work_start = f"{end_hour:02d}:{end_minute:02d}"
    work_end = f"{start_hour:02d}:{start_minute:02d}"
    
    # Проверяем статус режима "Сон по времени"
    sleep_time_status = "✅ ВКЛ" if time_restriction_middleware_instance.active else "❌ ВЫКЛ"
    sleep_manual_status = "✅ ВКЛ" if settings.sleep_manual_active else "❌ ВЫКЛ"
    
    text = (f"<b>⏰ Настройка времени сна</b>\n\n"
            f"<b>Статус режимов:</b>\n"
            f"💤 Мгновенный сон: {sleep_manual_status}\n"
            f"⏰ Сон по времени: {sleep_time_status}\n\n"
            f"<b>⏸️ Время сна (такси не работает):</b>\n"
            f"🕐 Начало: {start_hour:02d}:{start_minute:02d}\n"
            f"🕐 Окончание: {end_hour:02d}:{end_minute:02d}\n"
            f"💬 Сообщение: {message_text}\n\n"
            f"<b>✅ Режим работы такси:</b>\n"
            f"🕐 Часы работы: с {work_start} до {work_end}\n"
            f"📅 Рабочие дни: {work_days_text}\n"
            f"🚫 Выходные дни: {weekend_days_text}\n\n"
            f"Выберите, что хотите изменить:")
    
    await callback.message.answer(
        text=text,
        reply_markup=await kb_admin.sleep_time_kb(),
        parse_mode='HTML'
    )


@admin.callback_query(IsAdmin(), F.data == 'sleep_time_set_start_hour')
async def sleep_time_set_start_hour(callback: CallbackQuery, state: FSMContext):
    """Установить час начала времени сна"""
    await callback.answer('')
    try:
        await callback.message.answer(
            'Введите час начала времени сна (0-23):\n'
            'Например: 23 (23:00)',
            reply_markup=await kb.cancel_order()
        )
        await state.set_state(SleepTime.set_start_hour)
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)}')
        print(f'Ошибка в sleep_time_set_start_hour: {e}')
        import traceback
        traceback.print_exc()


@admin.callback_query(IsAdmin(), F.data == 'sleep_time_set_start_minute')
async def sleep_time_set_start_minute(callback: CallbackQuery, state: FSMContext):
    """Установить минуту начала времени сна"""
    await callback.answer('')
    try:
        await callback.message.answer(
            'Введите минуту начала времени сна (0-59):\n'
            'Например: 0, 30, 45',
            reply_markup=await kb.cancel_order()
        )
        await state.set_state(SleepTime.set_start_minute)
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)}')
        print(f'Ошибка в sleep_time_set_start_minute: {e}')
        import traceback
        traceback.print_exc()


@admin.callback_query(IsAdmin(), F.data == 'sleep_time_set_end_hour')
async def sleep_time_set_end_hour(callback: CallbackQuery, state: FSMContext):
    """Установить час окончания времени сна"""
    await callback.answer('')
    try:
        await callback.message.answer(
            'Введите час окончания времени сна (0-23):\n'
            'Например: 7 (7:00)',
            reply_markup=await kb.cancel_order()
        )
        await state.set_state(SleepTime.set_end_hour)
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)}')
        print(f'Ошибка в sleep_time_set_end_hour: {e}')
        import traceback
        traceback.print_exc()


@admin.callback_query(IsAdmin(), F.data == 'sleep_time_set_end_minute')
async def sleep_time_set_end_minute(callback: CallbackQuery, state: FSMContext):
    """Установить минуту окончания времени сна"""
    await callback.answer('')
    try:
        await callback.message.answer(
            'Введите минуту окончания времени сна (0-59):\n'
            'Например: 0, 30, 45',
            reply_markup=await kb.cancel_order()
        )
        await state.set_state(SleepTime.set_end_minute)
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)}')
        print(f'Ошибка в sleep_time_set_end_minute: {e}')
        import traceback
        traceback.print_exc()


@admin.callback_query(IsAdmin(), F.data == 'sleep_time_set_days')
async def sleep_time_set_days(callback: CallbackQuery, state: FSMContext):
    """Настройка дней недели для режима сна"""
    await callback.answer('')
    settings = await get_settings()
    current_days = format_sleep_days(settings.sleep_days if settings else None)
    await callback.message.answer(
        f'Текущие дни: {current_days}\n'
        f'Введите дни недели через запятую (1-7), где 1=Пн ... 7=Вс.\n'
        f'Например: 1,2,3,4,5 или 6,7',
        reply_markup=await kb.cancel_order()
    )
    await state.set_state(SleepTime.set_days)


@admin.callback_query(IsAdmin(), F.data == 'sleep_time_set_message')
async def sleep_time_set_message(callback: CallbackQuery, state: FSMContext):
    """Настройка сообщения при закрытом режиме"""
    await callback.answer('')
    settings = await get_settings()
    current_message = settings.sleep_message if settings and settings.sleep_message else "Извините, такси сейчас не работает"
    await callback.message.answer(
        f'Текущее сообщение:\n\n{current_message}\n\n'
        f'Отправьте новый текст (до 255 символов).',
        reply_markup=await kb.cancel_order()
    )
    await state.set_state(SleepTime.set_message)


@admin.message(IsAdmin(), SleepTime.set_start_hour, F.text)
async def sleep_time_save_start_hour(message: Message, state: FSMContext):
    """Сохранить час начала времени сна"""
    input_hour = message.text.strip()
    pattern = r"^(0|[1-9]|1[0-9]|2[0-3])$"  # 0-23
    
    if re.match(pattern, input_hour):
        hour = int(input_hour)
        await update_settings(sleep_start_hour=hour)
        
        settings = await get_settings()
        start_minute = settings.sleep_start_minute if settings and settings.sleep_start_minute is not None else 0
        await message.answer(f'Час начала времени сна установлен: {hour:02d}:{start_minute:02d}')
        await state.clear()
    else:
        await message.answer("Пожалуйста, введите число от 0 до 23.")


@admin.message(IsAdmin(), SleepTime.set_start_minute, F.text)
async def sleep_time_save_start_minute(message: Message, state: FSMContext):
    """Сохранить минуту начала времени сна"""
    input_minute = message.text.strip()
    pattern = r"^(0|[1-5]?[0-9])$"  # 0-59
    
    if re.match(pattern, input_minute):
        minute = int(input_minute)
        if 0 <= minute <= 59:
            await update_settings(sleep_start_minute=minute)
            
            settings = await get_settings()
            start_hour = settings.sleep_start_hour if settings and settings.sleep_start_hour is not None else 23
            await message.answer(f'Минута начала времени сна установлена: {start_hour:02d}:{minute:02d}')
            await state.clear()
        else:
            await message.answer("Пожалуйста, введите число от 0 до 59.")
    else:
        await message.answer("Пожалуйста, введите число от 0 до 59.")


@admin.message(IsAdmin(), SleepTime.set_end_hour, F.text)
async def sleep_time_save_end_hour(message: Message, state: FSMContext):
    """Сохранить час окончания времени сна"""
    input_hour = message.text.strip()
    pattern = r"^(0|[1-9]|1[0-9]|2[0-3])$"  # 0-23
    
    if re.match(pattern, input_hour):
        hour = int(input_hour)
        await update_settings(sleep_end_hour=hour)
        
        settings = await get_settings()
        end_minute = settings.sleep_end_minute if settings and settings.sleep_end_minute is not None else 0
        await message.answer(f'Час окончания времени сна установлен: {hour:02d}:{end_minute:02d}')
        await state.clear()
    else:
        await message.answer("Пожалуйста, введите число от 0 до 23.")


@admin.message(IsAdmin(), SleepTime.set_end_minute, F.text)
async def sleep_time_save_end_minute(message: Message, state: FSMContext):
    """Сохранить минуту окончания времени сна"""
    input_minute = message.text.strip()
    pattern = r"^(0|[1-5]?[0-9])$"  # 0-59
    
    if re.match(pattern, input_minute):
        minute = int(input_minute)
        if 0 <= minute <= 59:
            await update_settings(sleep_end_minute=minute)
            
            settings = await get_settings()
            end_hour = settings.sleep_end_hour if settings and settings.sleep_end_hour is not None else 7
            await message.answer(f'Минута окончания времени сна установлена: {end_hour:02d}:{minute:02d}')
            await state.clear()
        else:
            await message.answer("Пожалуйста, введите число от 0 до 59.")
    else:
        await message.answer("Пожалуйста, введите число от 0 до 59.")


@admin.message(IsAdmin(), SleepTime.set_days, F.text)
async def sleep_time_save_days(message: Message, state: FSMContext):
    """Сохранить дни недели для режима сна"""
    raw = message.text.replace(' ', '')
    pattern = r"^[1-7](,[1-7])*$"
    if re.match(pattern, raw):
        days_input = raw.split(',')
        # Преобразуем 1-7 в 0-6 для weekday()
        days = sorted({int(day) - 1 for day in days_input})
        await update_settings(sleep_days=days)
        
        # Показываем сохраненные дни, рабочие и выходные дни
        sleep_days_text = format_sleep_days(days)
        all_days = set(range(7))
        
        # Рабочие дни - это дни, которые В списке days (такси работает, кроме времени сна)
        work_days_set = sorted(days)
        work_days_text = ", ".join([WEEKDAY_LABELS[d] for d in work_days_set])
        
        # Выходные дни - это дни, которых НЕТ в списке days (такси закрыто весь день)
        weekend_days_set = sorted(all_days - set(days))
        if weekend_days_set:
            weekend_days_text = ", ".join([WEEKDAY_LABELS[d] for d in weekend_days_set])
        else:
            weekend_days_text = "Нет выходных"
        
        await message.answer(
            f'✅ <b>Дни сохранены</b>\n\n'
            f'📅 Дни сна: {sleep_days_text}\n'
            f'🚫 Выходные дни: {weekend_days_text}',
            parse_mode='HTML'
        )
        await state.clear()
    else:
        await message.answer("Введите числа 1-7 через запятую. Пример: 1,2,3,4,5")


@admin.message(IsAdmin(), SleepTime.set_message, F.text)
async def sleep_time_save_message(message: Message, state: FSMContext):
    """Сохранить сообщение для режима сна"""
    text = message.text.strip()
    if not text:
        await message.answer("Сообщение не может быть пустым. Введите текст сообщения.")
        return
    if len(text) > 255:
        await message.answer("Сообщение слишком длинное. Максимум 255 символов.")
        return
    await update_settings(sleep_message=text)
    
    await message.answer(f'✅ Сообщение сохранено:\n\n<b>{text}</b>', parse_mode='HTML')
    await state.clear()


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

    # Получаем время и сумму из настроек
    settings = await get_settings()
    if not settings:
        await callback.message.answer('Ошибка: настройки не найдены')
        return
    
    start_hour = settings.night_tariff_start_hour if settings.night_tariff_start_hour is not None else 0
    start_minute = settings.night_tariff_start_minute if settings.night_tariff_start_minute is not None else 0
    end_hour = settings.night_tariff_end_hour if settings.night_tariff_end_hour is not None else 7
    end_minute = settings.night_tariff_end_minute if settings.night_tariff_end_minute is not None else 0
    tariff_price = settings.night_tariff_price if settings.night_tariff_price is not None else 50
    
    print(f'Настройки из БД: начало {start_hour:02d}:{start_minute:02d}, окончание {end_hour:02d}:{end_minute:02d}, цена {tariff_price}')

    if answer == 'YES':
        try:
            # Удаляем старые задачи, если они есть (используем фиксированные глобальные ID)
            job_id1 = "set_night_price_global"
            job_id2 = "set_day_price_global"
            try:
                apscheduler.remove_job(job_id1)
                apscheduler.remove_job(job_id2)
            except JobLookupError:
                pass  # Задачи могут не существовать
            
            # Добавляем новые задачи с временем и суммой из БД
            apscheduler.add_job(city_routers_update_all,
                                trigger='cron',
                                hour=start_hour,
                                minute=start_minute,
                                id=job_id1,
                                args=[f'+{tariff_price}'],
                                )
            apscheduler.add_job(city_routers_update_all,
                                trigger='cron',
                                hour=end_hour,
                                minute=end_minute,
                                id=job_id2,
                                args=[f'-{tariff_price}'],
                                )
            
            # Показываем информацию о следующих запусках
            jobs = apscheduler.get_jobs()
            next_runs = []
            for job in jobs:
                if job.id in [job_id1, job_id2]:
                    next_run = job.next_run_time
                    if next_run:
                        next_runs.append(f"{job.id}: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            answer_text = (
                f'✅ Задача добавлена:\n'
                f'Начало ночного тарифа: {start_hour:02d}:{start_minute:02d} (+{tariff_price} руб)\n'
                f'Окончание ночного тарифа: {end_hour:02d}:{end_minute:02d} (-{tariff_price} руб)\n\n'
            )
            if next_runs:
                answer_text += "Следующие запуски:\n" + "\n".join(next_runs)
            
            await callback.message.answer(answer_text)
        except ConflictingIdError:
            await callback.message.answer('Задача уже добавлена')
            print('Ошибка запуска apscheduler.add_job')

    elif answer == 'NO':
        # Используем фиксированные глобальные ID
        job_id1 = "set_night_price_global"
        job_id2 = "set_day_price_global"
        print("Текущие задачи после добавления:", apscheduler.get_jobs())
        try:
            apscheduler.remove_job(job_id1)
            apscheduler.remove_job(job_id2)
            await callback.message.answer("Задача успешно отключена!")
        except JobLookupError:
            await callback.message.answer("Задача успешно отключена!")
            print('Ошибка остановки apscheduler.add_job')


# Ночной тариф
class NightTariff(StatesGroup):
    set_start_hour = State()
    set_start_minute = State()
    set_end_hour = State()
    set_end_minute = State()
    set_price = State()


@admin.callback_query(IsAdmin(), F.data == 'night_tariff_set_time')
async def night_tariff_set_time(callback: CallbackQuery):
    """Открыть настройки времени ночного тарифа"""
    await callback.answer('')
    settings = await get_settings()
    if not settings:
        await callback.message.answer('Ошибка: настройки не найдены')
        return
    
    start_hour = settings.night_tariff_start_hour if settings.night_tariff_start_hour is not None else 0
    start_minute = settings.night_tariff_start_minute if settings.night_tariff_start_minute is not None else 0
    end_hour = settings.night_tariff_end_hour if settings.night_tariff_end_hour is not None else 7
    end_minute = settings.night_tariff_end_minute if settings.night_tariff_end_minute is not None else 0
    
    print(f'Текущие настройки времени: начало {start_hour:02d}:{start_minute:02d}, окончание {end_hour:02d}:{end_minute:02d}')
    
    text = (f"<b>Настройка времени ночного тарифа</b>\n\n"
            f"Текущее время:\n"
            f"Начало: {start_hour:02d}:{start_minute:02d}\n"
            f"Окончание: {end_hour:02d}:{end_minute:02d}\n\n"
            f"Выберите, что хотите изменить:")
    
    await callback.message.edit_text(
        text=text,
        reply_markup=await kb_admin.night_tariff_time_kb(),
        parse_mode='HTML'
    )


@admin.callback_query(IsAdmin(), F.data == 'night_tariff_set_start_hour')
async def night_tariff_set_start_hour(callback: CallbackQuery, state: FSMContext):
    """Установить час начала ночного тарифа"""
    await callback.answer('')
    print(f'Обработчик night_tariff_set_start_hour вызван для callback: {callback.data}')
    try:
        await callback.message.answer(
            'Введите час начала ночного тарифа (0-23):\n'
            'Например: 0 (полночь), 22 (22:00)',
            reply_markup=await kb.cancel_order()
        )
        await state.set_state(NightTariff.set_start_hour)
        print(f'Состояние установлено: NightTariff.set_start_hour')
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)}')
        print(f'Ошибка в night_tariff_set_start_hour: {e}')
        import traceback
        traceback.print_exc()


@admin.callback_query(IsAdmin(), F.data == 'night_tariff_set_start_minute')
async def night_tariff_set_start_minute(callback: CallbackQuery, state: FSMContext):
    """Установить минуту начала ночного тарифа"""
    await callback.answer('')
    print(f'Обработчик night_tariff_set_start_minute вызван для callback: {callback.data}')
    try:
        await callback.message.answer(
            'Введите минуту начала ночного тарифа (0-59):\n'
            'Например: 0, 30, 45',
            reply_markup=await kb.cancel_order()
        )
        await state.set_state(NightTariff.set_start_minute)
        print(f'Состояние установлено: NightTariff.set_start_minute')
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)}')
        print(f'Ошибка в night_tariff_set_start_minute: {e}')
        import traceback
        traceback.print_exc()


@admin.callback_query(IsAdmin(), F.data == 'night_tariff_set_end_hour')
async def night_tariff_set_end_hour(callback: CallbackQuery, state: FSMContext):
    """Установить час окончания ночного тарифа"""
    await callback.answer('')
    print(f'Обработчик night_tariff_set_end_hour вызван для callback: {callback.data}')
    try:
        await callback.message.answer(
            'Введите час окончания ночного тарифа (0-23):\n'
            'Например: 7 (7:00), 8 (8:00)',
            reply_markup=await kb.cancel_order()
        )
        await state.set_state(NightTariff.set_end_hour)
        print(f'Состояние установлено: NightTariff.set_end_hour')
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)}')
        print(f'Ошибка в night_tariff_set_end_hour: {e}')
        import traceback
        traceback.print_exc()


@admin.callback_query(IsAdmin(), F.data == 'night_tariff_set_end_minute')
async def night_tariff_set_end_minute(callback: CallbackQuery, state: FSMContext):
    """Установить минуту окончания ночного тарифа"""
    await callback.answer('')
    print(f'Обработчик night_tariff_set_end_minute вызван для callback: {callback.data}')
    try:
        await callback.message.answer(
            'Введите минуту окончания ночного тарифа (0-59):\n'
            'Например: 0, 30, 45',
            reply_markup=await kb.cancel_order()
        )
        await state.set_state(NightTariff.set_end_minute)
        print(f'Состояние установлено: NightTariff.set_end_minute')
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)}')
        print(f'Ошибка в night_tariff_set_end_minute: {e}')
        import traceback
        traceback.print_exc()


@admin.callback_query(IsAdmin(), F.data == 'night_tariff_set_price')
async def night_tariff_set_price(callback: CallbackQuery, state: FSMContext):
    """Установить сумму ночного тарифа"""
    await callback.answer('')
    print(f'Обработчик night_tariff_set_price вызван для callback: {callback.data}')
    try:
        settings = await get_settings()
        if not settings:
            await callback.message.answer('Ошибка: настройки не найдены')
            return
        
        current_price = settings.night_tariff_price if settings.night_tariff_price is not None else 50
        print(f'Текущая сумма из БД: {current_price} (settings.night_tariff_price = {settings.night_tariff_price})')
        
        # Используем answer вместо edit_text, так как может быть конфликт с диалогами
        await callback.message.answer(
            f'<b>Настройка суммы ночного тарифа</b>\n\n'
            f'Текущая сумма: {current_price} рублей\n\n'
            f'Введите новую сумму (положительное число):\n'
            f'Например: 50, 75, 100',
            reply_markup=await kb.cancel_order(),
            parse_mode='HTML'
        )
        await state.set_state(NightTariff.set_price)
        print(f'Состояние установлено: NightTariff.set_price')
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)}')
        print(f'Ошибка в night_tariff_set_price: {e}')
        import traceback
        traceback.print_exc()


@admin.message(IsAdmin(), NightTariff.set_start_hour, F.text)
async def night_tariff_save_start_hour(message: Message, state: FSMContext, apscheduler: AsyncIOScheduler = None):
    """Сохранить час начала ночного тарифа"""
    input_hour = message.text.strip()
    pattern = r"^(0|[1-9]|1[0-9]|2[0-3])$"  # 0-23
    
    if re.match(pattern, input_hour):
        hour = int(input_hour)
        await update_settings(night_tariff_start_hour=hour)
        
        # Перезапускаем задачи, если они активны
        if apscheduler:
            print(f'apscheduler доступен, перезапускаем задачи...')
            await restart_night_tariff_jobs(message, apscheduler)
        else:
            print(f'apscheduler НЕ доступен!')
            await message.answer(
                f'Час начала ночного тарифа установлен: {hour:02d}:00\n'
                f'⚠️ Для применения изменений перезапустите ночной тариф вручную (Включить → Отключить → Включить)'
            )
            await state.clear()
            return
        
        settings = await get_settings()
        start_minute = settings.night_tariff_start_minute if settings and settings.night_tariff_start_minute is not None else 0
        await message.answer(f'Час начала ночного тарифа установлен: {hour:02d}:{start_minute:02d}')
        await state.clear()
    else:
        await message.answer("Пожалуйста, введите число от 0 до 23.")


@admin.message(IsAdmin(), NightTariff.set_start_minute, F.text)
async def night_tariff_save_start_minute(message: Message, state: FSMContext, apscheduler: AsyncIOScheduler = None):
    """Сохранить минуту начала ночного тарифа"""
    input_minute = message.text.strip()
    pattern = r"^(0|[1-5]?[0-9])$"  # 0-59
    
    if re.match(pattern, input_minute):
        minute = int(input_minute)
        if 0 <= minute <= 59:
            await update_settings(night_tariff_start_minute=minute)
            
            # Перезапускаем задачи, если они активны
            if apscheduler:
                print(f'apscheduler доступен, перезапускаем задачи...')
                await restart_night_tariff_jobs(message, apscheduler)
            else:
                print(f'apscheduler НЕ доступен!')
                settings = await get_settings()
                start_hour = settings.night_tariff_start_hour if settings and settings.night_tariff_start_hour is not None else 0
                await message.answer(
                    f'Минута начала ночного тарифа установлена: {start_hour:02d}:{minute:02d}\n'
                    f'⚠️ Для применения изменений перезапустите ночной тариф вручную (Включить → Отключить → Включить)'
                )
                await state.clear()
                return
            
            settings = await get_settings()
            start_hour = settings.night_tariff_start_hour if settings and settings.night_tariff_start_hour is not None else 0
            await message.answer(f'Минута начала ночного тарифа установлена: {start_hour:02d}:{minute:02d}')
            await state.clear()
        else:
            await message.answer("Пожалуйста, введите число от 0 до 59.")
    else:
        await message.answer("Пожалуйста, введите число от 0 до 59.")


@admin.message(IsAdmin(), NightTariff.set_end_hour, F.text)
async def night_tariff_save_end_hour(message: Message, state: FSMContext, apscheduler: AsyncIOScheduler = None):
    """Сохранить час окончания ночного тарифа"""
    input_hour = message.text.strip()
    pattern = r"^(0|[1-9]|1[0-9]|2[0-3])$"  # 0-23
    
    if re.match(pattern, input_hour):
        hour = int(input_hour)
        await update_settings(night_tariff_end_hour=hour)
        
        # Перезапускаем задачи, если они активны
        if apscheduler:
            print(f'apscheduler доступен, перезапускаем задачи...')
            await restart_night_tariff_jobs(message, apscheduler)
        else:
            print(f'apscheduler НЕ доступен!')
            await message.answer(
                f'Час окончания ночного тарифа установлен: {hour:02d}:00\n'
                f'⚠️ Для применения изменений перезапустите ночной тариф вручную (Включить → Отключить → Включить)'
            )
            await state.clear()
            return
        
        settings = await get_settings()
        end_minute = settings.night_tariff_end_minute if settings and settings.night_tariff_end_minute is not None else 0
        await message.answer(f'Час окончания ночного тарифа установлен: {hour:02d}:{end_minute:02d}')
        await state.clear()
    else:
        await message.answer("Пожалуйста, введите число от 0 до 23.")


@admin.message(IsAdmin(), NightTariff.set_end_minute, F.text)
async def night_tariff_save_end_minute(message: Message, state: FSMContext, apscheduler: AsyncIOScheduler = None):
    """Сохранить минуту окончания ночного тарифа"""
    input_minute = message.text.strip()
    pattern = r"^(0|[1-5]?[0-9])$"  # 0-59
    
    if re.match(pattern, input_minute):
        minute = int(input_minute)
        if 0 <= minute <= 59:
            await update_settings(night_tariff_end_minute=minute)
            
            # Перезапускаем задачи, если они активны
            if apscheduler:
                print(f'apscheduler доступен, перезапускаем задачи...')
                await restart_night_tariff_jobs(message, apscheduler)
            else:
                print(f'apscheduler НЕ доступен!')
                settings = await get_settings()
                end_hour = settings.night_tariff_end_hour if settings and settings.night_tariff_end_hour is not None else 7
                await message.answer(
                    f'Минута окончания ночного тарифа установлена: {end_hour:02d}:{minute:02d}\n'
                    f'⚠️ Для применения изменений перезапустите ночной тариф вручную (Включить → Отключить → Включить)'
                )
                await state.clear()
                return
            
            settings = await get_settings()
            end_hour = settings.night_tariff_end_hour if settings and settings.night_tariff_end_hour is not None else 7
            await message.answer(f'Минута окончания ночного тарифа установлена: {end_hour:02d}:{minute:02d}')
            await state.clear()
        else:
            await message.answer("Пожалуйста, введите число от 0 до 59.")
    else:
        await message.answer("Пожалуйста, введите число от 0 до 59.")


@admin.message(IsAdmin(), NightTariff.set_price, F.text)
async def night_tariff_save_price(message: Message, state: FSMContext, apscheduler: AsyncIOScheduler = None):
    """Сохранить сумму ночного тарифа"""
    input_price = message.text.strip()
    pattern = r"^\d+$"  # Только положительные числа
    
    if re.match(pattern, input_price):
        price = int(input_price)
        if price > 0:
            await update_settings(night_tariff_price=price)
            
            # Перезапускаем задачи, если они активны и apscheduler доступен
            if apscheduler:
                await restart_night_tariff_jobs(message, apscheduler)
            
            await message.answer(f'Сумма ночного тарифа установлена: {price} рублей')
            await state.clear()
        else:
            await message.answer("Сумма должна быть больше 0.")
    else:
        await message.answer("Пожалуйста, введите положительное число.")


async def restart_night_tariff_jobs(message: Message, apscheduler: AsyncIOScheduler):
    """Перезапустить задачи ночного тарифа с новым временем"""
    print(f'Перезапуск задач ночного тарифа...')
    # Используем фиксированные глобальные ID
    job_id1 = "set_night_price_global"
    job_id2 = "set_day_price_global"
    
    # Проверяем, есть ли активные задачи
    all_jobs = apscheduler.get_jobs()
    print(f'Всего задач в scheduler: {len(all_jobs)}')
    
    # Удаляем старые задачи ночного тарифа (если есть)
    try:
        apscheduler.remove_job(job_id1)
        print(f'Удалена задача: {job_id1}')
    except JobLookupError:
        print(f'Задача {job_id1} не найдена')
    
    try:
        apscheduler.remove_job(job_id2)
        print(f'Удалена задача: {job_id2}')
    except JobLookupError:
        print(f'Задача {job_id2} не найдена')
    
    # Получаем новое время и сумму из настроек
    settings = await get_settings()
    if not settings:
        await message.answer('Ошибка: настройки не найдены')
        return
    
    start_hour = settings.night_tariff_start_hour if settings.night_tariff_start_hour is not None else 0
    start_minute = settings.night_tariff_start_minute if settings.night_tariff_start_minute is not None else 0
    end_hour = settings.night_tariff_end_hour if settings.night_tariff_end_hour is not None else 7
    end_minute = settings.night_tariff_end_minute if settings.night_tariff_end_minute is not None else 0
    tariff_price = settings.night_tariff_price if settings.night_tariff_price is not None else 50
    
    print(f'Создаем новые задачи: начало {start_hour:02d}:{start_minute:02d}, окончание {end_hour:02d}:{end_minute:02d}, цена {tariff_price}')
    
    try:
        apscheduler.add_job(city_routers_update_all,
                            trigger='cron',
                            hour=start_hour,
                            minute=start_minute,
                            id=job_id1,
                            args=[f'+{tariff_price}'],
                            )
        print(f'Задача {job_id1} создана')
        apscheduler.add_job(city_routers_update_all,
                            trigger='cron',
                            hour=end_hour,
                            minute=end_minute,
                            id=job_id2,
                            args=[f'-{tariff_price}'],
                            )
        print(f'Задача {job_id2} создана')
        
        # Показываем информацию о следующих запусках
        jobs = apscheduler.get_jobs()
        next_runs = []
        for job in jobs:
            if job.id in [job_id1, job_id2]:
                next_run = job.next_run_time
                if next_run:
                    next_runs.append(f"{job.id}: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f'Следующий запуск {job.id}: {next_run}')
        
        answer_text = (
            f'\n✅ Задачи перезапущены:\n'
            f'Начало: {start_hour:02d}:{start_minute:02d} (+{tariff_price} руб)\n'
            f'Окончание: {end_hour:02d}:{end_minute:02d} (-{tariff_price} руб)\n\n'
        )
        if next_runs:
            answer_text += "Следующие запуски:\n" + "\n".join(next_runs)
        
        await message.answer(answer_text)
    except ConflictingIdError:
        await message.answer('Ошибка: Задача с таким ID уже существует. Возможно, она не была удалена.')
        print('Ошибка запуска apscheduler.add_job в restart_night_tariff_jobs: ConflictingIdError')
    except Exception as e:
        await message.answer(f'Ошибка при перезапуске задач: {str(e)}')
        print(f'Ошибка при перезапуске задач ночного тарифа: {e}')
        import traceback
        traceback.print_exc()


# Бесплатные поездки
class FreeOrder(StatesGroup):
    free_order_user = State()
    free_order_price = State()
    free_ride_cities = State()  # Для хранения выбранных городов


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
        new_free_price = int(input_int)
        
        # Получаем старое значение free_price
        old_settings = await get_settings()
        old_free_price = old_settings.free_price if old_settings else None
        
        # Обновляем настройку
        await update_settings(free_price=new_free_price)
        
        # Если новый порог меньше старого, корректируем счетчики пользователей
        if old_free_price is not None and new_free_price < old_free_price:
            updated_count = await adjust_user_free_ride_counters(new_free_price)
            if updated_count > 0:
                await message.answer(
                    f'Цена успешно изменена с {old_free_price} на {new_free_price}.\n'
                    f'Счетчик установлен в 1 для {updated_count} пользователей, '
                    f'у которых счетчик был {new_free_price} или выше.'
                )
            else:
                await message.answer(f'Цена успешно изменена с {old_free_price} на {new_free_price}.')
        else:
            await message.answer(f'Цена успешно изменена на {new_free_price}.')
        
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


@admin.callback_query(IsAdmin(), F.data == "free_ride_select_cities")
async def free_ride_select_cities(callback: CallbackQuery, state: FSMContext):
    """Открыть настройки выбора городов для бесплатной поездки"""
    await callback.answer('')
    settings = await get_settings()
    selected_city_ids = settings.free_ride_allowed_cities if settings and settings.free_ride_allowed_cities else []
    
    # Сохраняем в state
    await state.update_data(selected_city_ids=selected_city_ids)
    
    text = ("<b>Выбор городов для бесплатной поездки</b>\n\n"
            "Выберите города, которые будут доступны при выборе бесплатной поездки.\n"
            "Нажмите на город, чтобы добавить/убрать его из списка.\n"
            "После выбора нажмите 'Сохранить'.")
    
    await callback.message.edit_text(
        text=text,
        reply_markup=await kb_admin.free_ride_cities_kb(selected_city_ids),
        parse_mode='HTML'
    )


@admin.callback_query(IsAdmin(), F.data.startswith("toggle_free_city_"))
async def toggle_free_city(callback: CallbackQuery, state: FSMContext):
    """Переключить выбор города для бесплатной поездки"""
    await callback.answer('')
    city_id = int(callback.data.split('_')[-1])
    
    # Получаем из state
    data = await state.get_data()
    selected_city_ids = list(data.get('selected_city_ids', []))
    
    if city_id in selected_city_ids:
        selected_city_ids.remove(city_id)
    else:
        selected_city_ids.append(city_id)
    
    # Сохраняем обратно в state
    await state.update_data(selected_city_ids=selected_city_ids)
    
    # Обновляем клавиатуру
    text = ("<b>Выбор городов для бесплатной поездки</b>\n\n"
            "Выберите города, которые будут доступны при выборе бесплатной поездки.\n"
            "Нажмите на город, чтобы добавить/убрать его из списка.\n"
            "После выбора нажмите 'Сохранить'.")
    
    await callback.message.edit_text(
        text=text,
        reply_markup=await kb_admin.free_ride_cities_kb(selected_city_ids),
        parse_mode='HTML'
    )


@admin.callback_query(IsAdmin(), F.data == "save_free_cities")
async def save_free_cities(callback: CallbackQuery, state: FSMContext):
    """Сохранить выбранные города для бесплатной поездки"""
    await callback.answer('')
    
    # Получаем из state
    data = await state.get_data()
    selected_city_ids = data.get('selected_city_ids', [])
    
    # Сохраняем в базу
    await update_settings(free_ride_allowed_cities=selected_city_ids)
    
    await callback.message.edit_text(
        text="<b>Города успешно сохранены!</b>\n\n"
             f"Выбрано городов: {len(selected_city_ids)}\n\n"
             "Нажмите 'Назад' чтобы вернуться в меню.",
        reply_markup=await kb_admin.free_ride_cities_kb(selected_city_ids),
        parse_mode='HTML'
    )
    
    await state.clear()


# ------------------Принятие заказа админом---------------
# Обработчик удален - логика перенесена в handlers/user_group.py
# Админы принимают заказы через тот же обработчик, что и обычные водители
# Сообщения админам отправляются в других местах (dialog/callbacks.py, driver_handlers.py и т.д.)
