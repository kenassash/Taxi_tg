import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from app.database.models import async_main, engine

from config_reader import get_config, BotConfig
from handlers import routers_list
from app.common import menu, admin_menu
from app.dialog_info import info_menu
from app.dialog import start_menu_order, start_menu_dialog
from aiogram_dialog import setup_dialogs

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.admin import admin
from middleware.Scheduler_middleware import SchedulerMiddleware
from middleware.time_restriction_middleware import TimeRestrictionMiddleware
from app.driver_activity_check import send_activity_check_to_drivers, check_driver_activity_responses
from app.database.requests import get_settings

load_dotenv()

admin_list = [int(id.strip()) for id in os.getenv('CHAT_ID_ADMIN').split(",")]

async def main():
    await async_main()
    bot_config = get_config(BotConfig, "bot")
    bot = Bot(token=bot_config.token.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    scheduler = AsyncIOScheduler(timezone='Asia/Yakutsk')
    scheduler.start()

    # Настройки интервалов из БД (по умолчанию 2 часа и 10 минут)
    settings = await get_settings()
    interval_hours = settings.driver_check_interval_hours if settings and settings.driver_check_interval_hours else 2
    timeout_minutes = settings.driver_inactive_timeout_minutes if settings and settings.driver_inactive_timeout_minutes else 10

    # Задача: отправка проверок активности (интервал в часах, настраиваемый)
    scheduler.add_job(
        send_activity_check_to_drivers,
        trigger='interval',
        hours=interval_hours,
        id='driver_activity_check_send',
        args=[bot],
        replace_existing=True
    )

    # Задача: проверка ответов (частая, 1 мин; таймаут используется внутри функции)
    scheduler.add_job(
        check_driver_activity_responses,
        trigger='interval',
        minutes=1,
        id='driver_activity_check_responses',
        args=[bot],
        replace_existing=True
    )

    bot.my_admins_list = admin_list
    dp = Dispatcher(db_engine=engine)

    await bot.set_my_commands(commands=menu)
    await bot.set_my_commands(commands=admin_menu, scope=types.BotCommandScopeChat(chat_id=os.getenv('CHAT_ID_ADMIN')))

    dp.include_routers(admin)
    dp.callback_query.middleware(SchedulerMiddleware(scheduler))
    dp.message.middleware(SchedulerMiddleware(scheduler))  # Добавляем middleware и для message
    dp.include_routers(*routers_list)
    dp.include_routers(start_menu_order, start_menu_dialog)
    dp.include_routers(info_menu)


    setup_dialogs(dp)

    await dp.start_polling(bot)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')