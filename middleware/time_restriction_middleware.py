import asyncio
import os
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, Update, CallbackQuery
from datetime import datetime, time
import pytz
from app.database.requests import get_settings


WEEKDAY_LABELS = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}


def format_work_schedule(
    sleep_start_hour: int,
    sleep_start_minute: int,
    sleep_end_hour: int,
    sleep_end_minute: int,
    sleep_days: list[int] | None
) -> str:
    """Формирует строку режима работы на основе настроек времени сна."""
    work_start_hour = sleep_end_hour
    work_start_minute = sleep_end_minute
    work_end_hour = sleep_start_hour
    work_end_minute = sleep_start_minute

    work_start = f"{work_start_hour:02d}:{work_start_minute:02d}"
    work_end = f"{work_end_hour:02d}:{work_end_minute:02d}"

    if not sleep_days:
        work_days = "Все дни"
    else:
        all_days = set(range(7))
        work_days_set = sorted(all_days - set(sleep_days))
        if not work_days_set:
            work_days = "Нет рабочих дней"
        elif len(work_days_set) == 7:
            work_days = "Все дни"
        else:
            work_days_list = []
            i = 0
            while i < len(work_days_set):
                start = work_days_set[i]
                end = start
                while i + 1 < len(work_days_set) and work_days_set[i + 1] == end + 1:
                    i += 1
                    end = work_days_set[i]
                if start == end:
                    work_days_list.append(WEEKDAY_LABELS[start])
                else:
                    work_days_list.append(f"{WEEKDAY_LABELS[start]}-{WEEKDAY_LABELS[end]}")
                i += 1
            work_days = ", ".join(work_days_list)

    return f"Режим работы: {work_days} с {work_start} до {work_end}"


class TimeRestrictionMiddleware(BaseMiddleware):

    def __init__(self):
        self.timezone = pytz.timezone('Asia/Yakutsk')
        self.active = False  # По умолчанию middleware не активна

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:

        if not self.active:
            return await handler(event, data)

        # Получаем настройки времени сна из БД
        try:
            settings = await get_settings()
            if not settings:
                return await handler(event, data)

            # Получаем настройки
            start_hour = settings.sleep_start_hour if settings.sleep_start_hour is not None else 23
            start_minute = settings.sleep_start_minute if settings.sleep_start_minute is not None else 0
            end_hour = settings.sleep_end_hour if settings.sleep_end_hour is not None else 7
            end_minute = settings.sleep_end_minute if settings.sleep_end_minute is not None else 0
            days = settings.sleep_days if settings.sleep_days else list(range(7))
            
            # Формируем сообщение с режимом работы
            base_message = settings.sleep_message or "Извините, такси не работает"
            work_schedule = format_work_schedule(start_hour, start_minute, end_hour, end_minute, days)
            block_message = f"{base_message}, {work_schedule.lower()}"

            start_time = time(start_hour, start_minute)
            end_time = time(end_hour, end_minute)

            # Получение текущего времени и дня в заданном часовом поясе
            now = datetime.now(self.timezone)
            current_time = now.time()
            current_weekday = now.weekday()  # 0=Пн ... 6=Вс

            # Если текущий день не в списке, пропускаем проверку
            if current_weekday not in days:
                return await handler(event, data)

            # Проверяем, находится ли текущее время в диапазоне времени сна
            if start_time >= end_time:
                # Время сна переходит через полночь (например, 23:00 - 07:00)
                if current_time >= start_time or current_time < end_time:
                    if isinstance(event, Message):
                        await event.answer(block_message)
                        return
                    elif isinstance(event, CallbackQuery):
                        await event.answer(block_message, show_alert=True)
                        return
            else:
                # Время сна в пределах одного дня (например, 10:00 - 12:00)
                if start_time <= current_time < end_time:
                    if isinstance(event, Message):
                        await event.answer(block_message)
                        return
                    elif isinstance(event, CallbackQuery):
                        await event.answer(block_message, show_alert=True)
                        return
            
        except Exception as e:
            # В случае ошибки пропускаем проверку
            print(f"Ошибка в TimeRestrictionMiddleware: {e}")
            import traceback
            traceback.print_exc()

        return await handler(event, data)

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False
