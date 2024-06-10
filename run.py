import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from app.database.models import async_main
from handlers.handlers import router
from app.common import menu, admin_menu
from handlers.driver_handlers import driver_router
from handlers.shop_hanlders import shop_router

from handlers.user_group import user_group_router
from app.admin import admin
from middleware.time_restriction_middleware import TimeRestrictionMiddleware

load_dotenv()

admin_list = [int(id.strip()) for id in os.getenv('CHAT_ID_ADMIN').split(",")]
async def main():
    await async_main()
    bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bot.my_admins_list = admin_list
    dp = Dispatcher()

    await bot.set_my_commands(commands=menu, scope=types.BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(commands=admin_menu, scope=types.BotCommandScopeChat(chat_id=os.getenv('CHAT_ID_ADMIN')))
    dp.include_routers(admin, user_group_router, router, driver_router, shop_router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')