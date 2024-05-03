import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from app.database.models import async_main
from app.handlers import router
from app.common import menu

from handlers.user_group import user_group_router
from app.admin import admin


async def main():
    await async_main()
    load_dotenv()
    bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bot.my_admins_list = [216159472]
    dp = Dispatcher()
    await bot.set_my_commands(commands=menu, scope=types.BotCommandScopeAllPrivateChats())
    # await bot.set_my_commands(commands=driver_menu, scope=types.BotCommandScopeAllGroupChats())
    dp.include_routers(admin, user_group_router, router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')