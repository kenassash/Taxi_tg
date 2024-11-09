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
from app.dialog import start_menu_order, start_menu_dialog
from aiogram_dialog import setup_dialogs

from app.admin import admin
from middleware.time_restriction_middleware import TimeRestrictionMiddleware

load_dotenv()

admin_list = [int(id.strip()) for id in os.getenv('CHAT_ID_ADMIN').split(",")]
# async def main():
#     await async_main()
#     bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
#     bot.my_admins_list = admin_list
#     dp = Dispatcher()
#
#     await bot.set_my_commands(commands=menu, scope=types.BotCommandScopeAllPrivateChats())
#     await bot.set_my_commands(commands=admin_menu, scope=types.BotCommandScopeChat(chat_id=os.getenv('CHAT_ID_ADMIN')))
#     dp.include_routers(admin)
#     dp.include_routers(*routers_list)
#     dp.include_routers(start_menu_order, start_menu_dialog)
#     setup_dialogs(dp)
#     await dp.start_polling(bot)
async def main():
    await async_main()
    bot_config = get_config(BotConfig, "bot")
    bot = Bot(token=bot_config.token.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    bot.my_admins_list = admin_list
    dp = Dispatcher(db_engine=engine)

    await bot.set_my_commands(commands=menu, scope=types.BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(commands=admin_menu, scope=types.BotCommandScopeChat(chat_id=os.getenv('CHAT_ID_ADMIN')))
    dp.include_routers(admin)
    dp.include_routers(*routers_list)
    dp.include_routers(start_menu_order, start_menu_dialog)
    setup_dialogs(dp)

    await dp.start_polling(bot)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')