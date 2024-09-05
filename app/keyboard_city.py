from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.database.requests import get_cities_inside, get_cities_outside


# locations = {
#     "Анновка": 2700,
#     "Архара": 5800,
#     "Аэропорт": 5500,
#     "Борисоглебка": 1800,
#     "Благовещенск": 4800,
#     "Белогорск": 3500,
#     "Беляковка": 1900,
#     "Березовка": 4300,
#     "Верхнебелое": 1400,
#     "Владимировка": 4500,
#     "Вознесеновка": 2300,
#     "Высокое": 1500,
#     "Возжаевка": 2300,
#     "Варваровка": 1800,
#     "Георгиевка": 800,  # исправлено с 1400
#     "Долдыкан": 3200,
#     "Дальневосточное": 1300,
#     "Зорино": 800,
#     "Завитинск": 1600,
#     "Знаменка": 1500,
#     "Серышево": 4200,
#     "Трудовой": 1900,
#     "Талакан": 4200,
#     "Тамбовка": 3200,
#     "Ивановка": 3500,
#     "Ильиновка": 2300,
#     "Короли (федералка)": 850,
#     "Короли": 700,
#     "Козьмодемьяновка": 2000,
#     "Каховка": 2350,
#     "Кутилово": 1400,
#     "Климовка": 2300,
#     "Любимое": 1800,
#     "Максимовка": 1200,
#     "МПС (нефть)": 750,
#     "Мухинский": 1300,
#     "Марьяновка": 1100,
#     "Морозова": 2000,
#     "Николо-Александровка": 1700,
#     "Нагорный": 400,
#     "Новомихайловка": 850,
#     "Заречное (Белогорский р-он)": 2600,
#     "Преображеновка": 1400,
#     "Прогресс": 4200,
#     "Песчаноозёрка": 1400,
#     "Поярково": 4200,
#     "Поздеевка (федералка)": 1800,
#     "Переяславка": 1000,
#     "Прибрежный": 450,
#     "Покровка": 1500,
#     "Панино": 250,
#     "Романовка": 750,
#     "Ромны": 2000,
#     "Райчихинск": 3500,
#     "Рогозовка": 1700,
#     "Смелое": 1200,
#     "Среднебелая": 4500,
#     "Сергеев-Фёдоровка": 1000,
#     "Свободный": 6000,
#     "Смирновка (федералка)": 1200,
#     "Святорусовка": 1200,
#     "Солнечное": 4500,  # исправлено с 4000
#     "Новоросийка": 1800,
#     "Новобурейский": 3500,
#     "Новокиевский Увал": 6500,
#     "Урожайное": 750,
#     "Чигири": 4800,
#     "Черёмушки": 1200,
#     "Шимановск": 8600,
#     "Харьковка": 140,  # исправлено
#     "Южное": 200,  # исправлено с 400
#     "Ерковцы": 2200,
#     "Ясная Поляна": 1600
# }


# cities = {
#     "Екатеринославка": 150,
#     "Таёжный": 200,
#     "Полигон": 350,
#     "Восточный за ж/д": 200,
#     "Агрохолдинг": 300,
# }


async def keyboard_city1():
    keyboard = InlineKeyboardBuilder()
    cities = await get_cities_inside()
    for city in cities:
        keyboard.add(InlineKeyboardButton(text=city.city_name,
                                          callback_data=f'cities1_{city.city_name}_{city.price}'))
    keyboard.add(InlineKeyboardButton(text='Другой нп', callback_data=f'citiesoutside1_'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()


async def keyboard_city2():
    keyboard = InlineKeyboardBuilder()
    # cities = await get_cities_outside()
    cities = await get_cities_inside()
    for city in cities:
        keyboard.add(InlineKeyboardButton(text=city.city_name,
                                          callback_data=f'cities2_{city.city_name}_{city.price}'))
    keyboard.add(InlineKeyboardButton(text='Другой нп', callback_data=f'citiesoutside2_'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data=f'backbutton_'))
    return keyboard.adjust(2).as_markup()


async def keyboard_city3():
    keyboard = InlineKeyboardBuilder()
    cities = await get_cities_outside()
    for city in cities:
        keyboard.add(InlineKeyboardButton(text=city.city_name,
                                          callback_data=f'cities1_{city.city_name}_{city.price}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data=f'backbutton_'))
    return keyboard.adjust(2).as_markup()


async def keyboard_city4():
    keyboard = InlineKeyboardBuilder()
    cities = await get_cities_outside()
    for city in cities:
        keyboard.add(InlineKeyboardButton(text=city.city_name,
                                          callback_data=f'cities2_{city.city_name}_{city.price}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data=f'backbutton_'))
    return keyboard.adjust(2).as_markup()
