from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, CallbackQuery, Message
from app.database.requests import get_driver, get_settings
from app.driver_activity_check import update_driver_last_interaction

class DriverActiveMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Извлекаем событие из Update, если это Update
        actual_event = event
        if hasattr(event, 'callback_query') and event.callback_query:
            actual_event = event.callback_query
        elif hasattr(event, 'message') and event.message:
            actual_event = event.message
        
        # Отслеживаем все взаимодействия водителей для проверки активности
        user_id = None
        if hasattr(actual_event, 'from_user') and actual_event.from_user:
            user_id = actual_event.from_user.id
        
        if user_id:
            driver = await get_driver(user_id)
            if driver:
                # Обновляем время последнего взаимодействия водителя
                update_driver_last_interaction(user_id)
        
        # Проверка при принятии заказа
        if isinstance(actual_event, CallbackQuery) and hasattr(actual_event, 'data') and actual_event.data and actual_event.data.startswith('accept_'):
            driver = await get_driver(actual_event.from_user.id)
            
            if not driver:
                await actual_event.answer("Ошибка: вы не найдены в системе водителей.", show_alert=True)
                return
            
            # Проверяем баланс водителя
            try:
                driver_price_raw = driver.price
                driver_balance = driver_price_raw if driver_price_raw is not None else 0
            except Exception as e:
                driver_balance = 0
            
            if driver_balance <= 0:
                await actual_event.answer(
                    "Вы не можете принять заказ, так как у вас недостаточно средств на балансе.",
                    show_alert=True
                )
                return
            
            # Проверяем автораспределение
            settings = await get_settings()
            auto_distribution = settings.auto_distribution if settings else False
            
            # Если автораспределение включено, проверяем активность водителя
            if auto_distribution:
                if not driver.active:
                    await actual_event.answer("Вы не активны и не можете принимать заказы.", show_alert=True)
                    return
            # Если автораспределение выключено, не проверяем активность - водитель может принимать заказы
        return await handler(event, data)
