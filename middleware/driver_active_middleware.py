from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, CallbackQuery
from app.database.requests import get_driver, get_settings

class DriverActiveMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, CallbackQuery) and event.data.startswith('accept_'):
            driver = await get_driver(event.from_user.id)
            
            if not driver:
                await event.answer("Ошибка: вы не найдены в системе водителей.", show_alert=True)
                return
            
            # Проверяем баланс водителя
            try:
                driver_price_raw = driver.price
                driver_balance = driver_price_raw if driver_price_raw is not None else 0
            except Exception as e:
                driver_balance = 0
            
            if driver_balance <= 0:
                await event.answer(
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
                    await event.answer("Вы не активны и не можете принимать заказы.", show_alert=True)
                    return
            # Если автораспределение выключено, не проверяем активность - водитель может принимать заказы
        return await handler(event, data)
