from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.database.requests import get_all_car, get_cities_inside, get_cities_outside, \
    get_cities_routes1, get_cities_routes2


# async def admin_keyboard():
#     keyboard = InlineKeyboardBuilder()
#     keyboard.add(InlineKeyboardButton(text='Автомобили', callback_data='car_menu'))
#     keyboard.add(InlineKeyboardButton(text='Информация', callback_data='info'))
#     keyboard.add(InlineKeyboardButton(text='Рассылка', callback_data='newletter'))
#     keyboard.add(InlineKeyboardButton(text='Поменять цену', callback_data='change_settings'))
#     keyboard.add(InlineKeyboardButton(text='Пользователи', callback_data='number_passeger'))
#     keyboard.add(InlineKeyboardButton(text='Бан', callback_data='ban_user'))
#     keyboard.add(InlineKeyboardButton(text='Время сна', callback_data='time_restriction'))
#     keyboard.add(InlineKeyboardButton(text='Запрет водителю', callback_data='driver_block'))
#     keyboard.add(InlineKeyboardButton(text='Инф-ия о заказе', callback_data='info_order'))
#     keyboard.add(InlineKeyboardButton(text='Ночной тариф', callback_data='nightchange'))
#     keyboard.add(InlineKeyboardButton(text='Сделать бесплатную поздку', callback_data='freeorder'))
#     keyboard.add(InlineKeyboardButton(text='Пополнить баланс водителю', callback_data='add_balance'))
#     keyboard.add(InlineKeyboardButton(text='Автораспределение', callback_data='auto_distribution'))
#     keyboard.add(InlineKeyboardButton(text='Вкл бесплатные поездки', callback_data='free_ride'))
#     return keyboard.adjust(2).as_markup()

def create_keyboard(
        buttons: dict[str, str],
        adjust: int
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, callback in buttons.items():
        builder.button(
            text=text,
            callback_data=callback
        )
    builder.adjust(adjust)
    return builder.as_markup()

def admin_keyboard(
        auto_distribution: bool = False,
        free_ride: bool = False,
) -> InlineKeyboardMarkup:
    buttons = {
        'Автомобили': 'car_menu',
        'Информация': 'info',
        'Рассылка': 'newletter',
        'Поменять цену': 'change_settings',
        'Пользователи': 'number_passeger',
        'Бан': 'ban_user',
        'Время сна': 'time_restriction',
        'Активность водителей': 'driver_block',
        'Список водителей': 'drivers_list',
        'Интервал смс': 'driver_activity',
        'Инф-ия о заказе': 'info_order',
        'Ночной тариф': 'nightchange',
        'Настройка бесплатных': 'freeorder',
        'Пополнить баланс водителю': 'add_balance',
        # "Автораспределение": "auto_distribution"
    }
    if auto_distribution:
        buttons["Автораспределение(Вкл)"] = "auto_distribution"
    else:
        buttons["Автораспределение(Выкл)"] = "auto_distribution"
    if free_ride:
        buttons["Бесплатная поездка(Вкл)"] = "free_ride"
    else:
        buttons["Бесплатная поездка(Выкл)"] = "free_ride"
    return create_keyboard(
        buttons=buttons,
        adjust=2
    )


async def turn_time_rest(sleep_manual_active: bool = False, sleep_time_active: bool = False):
    """Клавиатура для управления режимами сна"""
    keyboard = InlineKeyboardBuilder()
    
    # Мгновенный сон (без времени)
    if sleep_manual_active:
        keyboard.add(InlineKeyboardButton(text='💤 Сон сразу: ВКЛ', callback_data='sleep_manual_OFF'))
    else:
        keyboard.add(InlineKeyboardButton(text='💤 Сон сразу: ВЫКЛ', callback_data='sleep_manual_ON'))
    
    # Сон по времени
    if sleep_time_active:
        keyboard.add(InlineKeyboardButton(text='⏰ Сон по времени: ВКЛ', callback_data='turntimerest_NO'))
    else:
        keyboard.add(InlineKeyboardButton(text='⏰ Сон по времени: ВЫКЛ', callback_data='turntimerest_YES'))
    
    keyboard.add(InlineKeyboardButton(text='Настроить время', callback_data='sleep_time_set_time'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(1).as_markup()


async def sleep_time_kb():
    """Клавиатура для настройки времени сна"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Изменить час начала', callback_data='sleep_time_set_start_hour'))
    keyboard.add(InlineKeyboardButton(text='Изменить минуту начала', callback_data='sleep_time_set_start_minute'))
    keyboard.add(InlineKeyboardButton(text='Изменить час окончания', callback_data='sleep_time_set_end_hour'))
    keyboard.add(InlineKeyboardButton(text='Изменить минуту окончания', callback_data='sleep_time_set_end_minute'))
    keyboard.add(InlineKeyboardButton(text='Изменить дни недели', callback_data='sleep_time_set_days'))
    keyboard.add(InlineKeyboardButton(text='Изменить сообщение', callback_data='sleep_time_set_message'))
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data='time_restriction'))
    return keyboard.adjust(1).as_markup()


async def driver_activity_kb():
    """Клавиатура для настройки интервалов проверки активности водителей"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Изменить интервал (часы)', callback_data='driver_activity_set_interval'))
    keyboard.add(InlineKeyboardButton(text='Изменить таймаут (минуты)', callback_data='driver_activity_set_timeout'))
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data='admin_back'))
    return keyboard.adjust(1).as_markup()


async def car_menu_keyboard():
    keyboard = InlineKeyboardBuilder()
    # keyboard.add(InlineKeyboardButton(text='Добавить', callback_data='add_car'))
    keyboard.add(InlineKeyboardButton(text='Изменить', callback_data='edit_car'))
    keyboard.add(InlineKeyboardButton(text='Удалить', callback_data='delete_car'))
    return keyboard.adjust(3).as_markup()


async def edit_car():
    drivers = await get_all_car()
    keyboard = InlineKeyboardBuilder()
    for driver in drivers:
        keyboard.add(InlineKeyboardButton(text=f'{driver.name} - {driver.number_car}',
                                          callback_data=f'editcar_{driver.id}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()


async def delete_car():
    drivers = await get_all_car()
    keyboard = InlineKeyboardBuilder()
    for driver in drivers:
        keyboard.add(InlineKeyboardButton(text=f'{driver.name} - {driver.number_car}',
                                          callback_data=f'deletecar_{driver.id}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()


async def all_car():
    drivers = await get_all_car()
    keyboard = InlineKeyboardBuilder()
    for driver in drivers:
        keyboard.add(InlineKeyboardButton(text=f'{driver.name} - {driver.number_car}',
                                          callback_data=f'infocardriver_{driver.id}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()



async def add_balance():
    drivers = await get_all_car()
    keyboard = InlineKeyboardBuilder()
    for driver in drivers:
        keyboard.add(InlineKeyboardButton(text=f'{driver.name} - {driver.number_car}',
                                          callback_data=f'addbalance_{driver.id}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()

async def change_money():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text=f'Целиком связку', callback_data=f'changerouters'))
    keyboard.add(InlineKeyboardButton(text='Другой нп', callback_data=f'changeoutside'))
    keyboard.add(InlineKeyboardButton(text='По отдельности ', callback_data=f'change_point_start_end'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(3).as_markup()


# async def change_mouney_inside():
#     keyboard = InlineKeyboardBuilder()
#     cities = await get_cities_inside()
#     for city in cities:
#         keyboard.add(InlineKeyboardButton(text=city.city_name,
#                                           callback_data=f'chin_{city.city_name}_{city.price}'))
#     keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
#     return keyboard.adjust(2).as_markup()


async def change_mouney_outside():
    keyboard = InlineKeyboardBuilder()
    cities = await get_cities_outside()
    for city in cities:
        keyboard.add(InlineKeyboardButton(text=city.city_name,
                                          callback_data=f'chout_{city.city_name}_{city.price}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()

async def change_mouney_routes1():
    keyboard = InlineKeyboardBuilder()
    cities = await get_cities_routes1()
    for city in cities:
        keyboard.add(InlineKeyboardButton(text=city.city1,
                                          callback_data=f'chroute_{city.city1}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()

async def change_mouney_routes2(city1: str):
    keyboard = InlineKeyboardBuilder()
    cities = await get_cities_routes2(city1)
    for city in cities:
        keyboard.add(InlineKeyboardButton(text=city,
                                          callback_data=f'finroute_{city}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()


async def ban_users_phone():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Забанить', callback_data=f'ban_add'))
    keyboard.add(InlineKeyboardButton(text='Разбанить', callback_data=f'ban_no'))
    keyboard.add(InlineKeyboardButton(text='Список', callback_data=f'ban_list'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()


async def send_to_user():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Ответить', callback_data=f'sendTouser'))
    return keyboard.adjust().as_markup()

async def button_deactive():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Не активен', callback_data=f'blockdrive_YES'))
    keyboard.add(InlineKeyboardButton(text='Активен', callback_data=f'blockdrive_NO'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()


async def driver_no_active():
    drivers = await get_all_car()
    keyboard = InlineKeyboardBuilder()
    for driver in drivers:
        keyboard.add(InlineKeyboardButton(text=f'{driver.name} - {driver.number_car}',
                                          callback_data=f'noactive_{driver.id}'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()

async def night_changekb():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Включить', callback_data='nightchangekb_YES'))
    keyboard.add(InlineKeyboardButton(text='Отключить', callback_data='nightchangekb_NO'))
    keyboard.add(InlineKeyboardButton(text='Настроить время', callback_data='night_tariff_set_time'))
    keyboard.add(InlineKeyboardButton(text='Настроить сумму', callback_data='night_tariff_set_price'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()

async def night_tariff_time_kb():
    """Клавиатура для настройки времени ночного тарифа"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Изменить час начала', callback_data='night_tariff_set_start_hour'))
    keyboard.add(InlineKeyboardButton(text='Изменить минуту начала', callback_data='night_tariff_set_start_minute'))
    keyboard.add(InlineKeyboardButton(text='Изменить час окончания', callback_data='night_tariff_set_end_hour'))
    keyboard.add(InlineKeyboardButton(text='Изменить минуту окончания', callback_data='night_tariff_set_end_minute'))
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data='nightchange'))
    return keyboard.adjust(1).as_markup()

async def free_order_kb():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Дать бп', callback_data='add_freeorder'))
    keyboard.add(InlineKeyboardButton(text='Изменить цифру бп', callback_data='chn_freeorder'))
    keyboard.add(InlineKeyboardButton(text='Выбрать города для БП', callback_data='free_ride_select_cities'))
    keyboard.add(InlineKeyboardButton(text='Отменить', callback_data=f'cancelorder_'))
    return keyboard.adjust(2).as_markup()

async def free_ride_cities_kb(selected_city_ids: list[int] | None = None):
    """Клавиатура для выбора городов доступных при бесплатной поездке"""
    from app.database.requests import get_settings
    from app.database.requests import get_cities_inside
    
    if selected_city_ids is None:
        settings = await get_settings()
        selected_city_ids = settings.free_ride_allowed_cities if settings and settings.free_ride_allowed_cities else []
    
    # Преобразуем в set для быстрой проверки
    selected_city_ids_set = set(selected_city_ids) if selected_city_ids else set()
    cities = await get_cities_inside()
    
    keyboard = InlineKeyboardBuilder()
    
    for city in cities:
        if city.id in selected_city_ids_set:
            text = f"✓ {city.city_name}"
        else:
            text = f"  {city.city_name}"
        keyboard.add(InlineKeyboardButton(
            text=text,
            callback_data=f'toggle_free_city_{city.id}'
        ))
    
    keyboard.add(InlineKeyboardButton(text='Сохранить', callback_data='save_free_cities'))
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data='freeorder'))
    
    keyboard.adjust(1)
    return keyboard.as_markup()
