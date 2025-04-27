from aiogram.types import BotCommand

menu= [
    BotCommand(command='start', description='Сделать заказ'),
    BotCommand(command='info', description='Информация по другому населенному пункту'),
    BotCommand(command='manager', description='Поддержка'),
]

admin_menu = [
    BotCommand(command='start', description='Сделать заказ'),
    BotCommand(command='admin', description='Админ панель'),
    BotCommand(command='info', description='Информация по другому населенному пункту'),
    BotCommand(command='manager', description='Поддержка'),
]