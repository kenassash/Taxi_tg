"""
Модуль для проверки активности водителей:
- Отправка сообщений через настраиваемый интервал (часы)
- Автоматическая установка неактивности через настраиваемый таймаут (минуты)
"""
from datetime import datetime, timedelta
from typing import Dict
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from app.database.requests import (
    get_all_active_drivers,
    update_driver,
    mark_driver_inactive,
    get_settings,
)
import app.keyboards as kb

# Хранилище времени отправки запросов активности
# Ключ: tg_id водителя, Значение: datetime отправки запроса
activity_check_requests: Dict[int, datetime] = {}

# Хранилище времени последнего взаимодействия водителя
# Ключ: tg_id водителя, Значение: datetime последнего взаимодействия
driver_last_interaction: Dict[int, datetime] = {}


async def _get_timeout_minutes() -> int:
    settings = await get_settings()
    if settings and settings.driver_inactive_timeout_minutes is not None:
        return max(1, settings.driver_inactive_timeout_minutes)
    return 10


async def _get_interval_hours() -> int:
    """Получить интервал проверки активности в часах"""
    settings = await get_settings()
    if settings and settings.driver_check_interval_hours is not None:
        return max(1, settings.driver_check_interval_hours)
    return 1


def update_driver_last_interaction(driver_tg_id: int):
    """Обновить время последнего взаимодействия водителя"""
    driver_last_interaction[driver_tg_id] = datetime.now()
    # Если водитель ответил на запрос активности, удаляем его из списка ожидающих
    if driver_tg_id in activity_check_requests:
        del activity_check_requests[driver_tg_id]


async def send_activity_check_to_drivers(bot: Bot):
    """Отправляет сообщение с проверкой активности водителям, если прошло больше часа с последнего взаимодействия"""
    # Проверяем, включено ли автораспределение
    settings = await get_settings()
    if not settings or not settings.auto_distribution:
        print("Автораспределение выключено - проверка активности не выполняется")
        return
    
    drivers = await get_all_active_drivers()
    if not drivers:
        print("Нет активных водителей для проверки")
        return

    current_time = datetime.now()
    sent_count = 0
    failed_count = 0
    skipped_count = 0
    timeout_minutes = await _get_timeout_minutes()
    interval_hours = await _get_interval_hours()

    for driver in drivers:
        # Проверяем, прошло ли больше часа с последнего взаимодействия
        last_interaction = driver_last_interaction.get(driver.tg_id)
        
        # Если водитель уже получил запрос активности и еще не ответил - пропускаем
        if driver.tg_id in activity_check_requests:
            skipped_count += 1
            continue
        
        # Если есть время последнего взаимодействия и прошло меньше часа - пропускаем
        if last_interaction:
            time_since_interaction = current_time - last_interaction
            if time_since_interaction < timedelta(hours=interval_hours):
                skipped_count += 1
                continue
        
        # Если нет времени последнего взаимодействия или прошло больше часа - отправляем запрос
        try:
            await bot.send_message(
                chat_id=driver.tg_id,
                text="❓ <b>Вы активны или нет?</b>\n\n"
                     f"Пожалуйста, подтвердите вашу активность. Если не ответите в течение {timeout_minutes} минут, вы будете автоматически переведены в неактивный статус.",
                reply_markup=await kb.driver_activity_check()
            )
            activity_check_requests[driver.tg_id] = current_time
            sent_count += 1
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                print(f"Водитель {driver.tg_id} заблокировал бота")
                await mark_driver_inactive(driver.tg_id)
                failed_count += 1
            else:
                print(f"Ошибка отправки сообщения водителю {driver.tg_id}: {e}")
                failed_count += 1
        except Exception as e:
            print(f"Неожиданная ошибка при отправке сообщения водителю {driver.tg_id}: {e}")
            failed_count += 1

    print(f"Проверка активности: отправлено {sent_count}, пропущено {skipped_count}, ошибок {failed_count}")


async def check_driver_activity_responses(bot: Bot):
    """Проверяет ответы водителей и ставит неактивными тех, кто не ответил в течение настроенного таймаута"""
    # Проверяем, включено ли автораспределение
    settings = await get_settings()
    if not settings or not settings.auto_distribution:
        # Если автораспределение выключено, очищаем все ожидающие ответы
        activity_check_requests.clear()
        return
    
    current_time = datetime.now()
    timeout_minutes = await _get_timeout_minutes()
    inactive_count = 0

    requests_copy = activity_check_requests.copy()

    for driver_tg_id, request_time in requests_copy.items():
        if current_time - request_time >= timedelta(minutes=timeout_minutes):
            try:
                await mark_driver_inactive(driver_tg_id)
                del activity_check_requests[driver_tg_id]
                inactive_count += 1
                print(f"Водитель {driver_tg_id} переведен в неактивный статус (нет ответа на проверку активности)")
            except Exception as e:
                print(f"Ошибка при установке неактивности водителю {driver_tg_id}: {e}")

    if inactive_count > 0:
        print(f"Проверка активности: {inactive_count} водителей переведены в неактивный статус")


def mark_driver_responded(driver_tg_id: int):
    """Отмечает, что водитель ответил на запрос активности"""
    update_driver_last_interaction(driver_tg_id)

