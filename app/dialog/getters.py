from aiogram_dialog import DialogManager

from app.change_price import Settings
from app.database.requests import (
    get_all_orders,
    set_chat_id_driver,
    get_cities_inside,
    get_cities_outside,
    get_route_price,
    get_user,
    get_cities_outside_name
)
from app.dialog.callbacks import update_price


async def get_role_driver(dialog_manager: DialogManager, **kwargs):
    driver = dialog_manager.middleware_data['driver']
    text = f'<b>Добро пожаловать, Таксист {dialog_manager.event.from_user.full_name}</b>😊\n\n'
    data = {'text': text}
    return data
async def get_role_user(dialog_manager: DialogManager, **kwargs):
    try:
        text = f'<b>Добро пожаловать, {dialog_manager.event.from_user.full_name}!</b> 😊\n\n' \
            # f'До бесплатной поездки осталось <b>{Settings.free_ride - user.free_ride}</b>'
        data = {'text': text}
        return data
    except KeyError:
        text = f'Нажмите на кнопку'
        data = {'text': text}
        return data

async def get_role_guest(dialog_manager: DialogManager, **kwargs):
    text = f'Добро пожаловать в такси городок!\n' \
           f'Пожалуйста, отправьте свой номер телефона для регистрации с помощью кнопки:'
    data = {'text': text}
    return data



async def get_upprice(dialog_manager: DialogManager, **kwargs):

    order_id_id = dialog_manager.dialog_data.get('order_id')
    order_data = await get_all_orders(order_id_id)
    current_stack = dialog_manager.current_stack()
    message_id = current_stack.last_message_id
    await set_chat_id_driver(order_id_id, message_id)
    if dialog_manager.dialog_data.get('add_address'):
        data = {
            "city1_id": order_data.city1_id,
            "city2_id": order_data.city2_id,
            "address1_id": order_data.address1_id,
            "address2_id": order_data.address2_id,
            "add_address": dialog_manager.dialog_data.get('add_address'),
            "price": order_data.price,
            'first_show': True,
        }
        return data

    data = {
        "city1_id": order_data.city1_id,
        "city2_id": order_data.city2_id,
        "address1_id": order_data.address1_id,
        "address2_id": order_data.address2_id,
        "price": order_data.price,
        'first_show': False,
    }
    return data





async def get_city_inside1(dialog_manager: DialogManager, **kwargs, ):
    cities = await get_cities_inside()
    data = {
        'city_inside1': cities,
    }
    return data


async def get_city_inside2(dialog_manager: DialogManager, **kwargs, ):
    cities = await get_cities_inside()
    adress1_id = dialog_manager.dialog_data.get('address1_id')
    city1_id = dialog_manager.dialog_data.get('city1_id')
    another_id = dialog_manager.dialog_data.get('another1_id')

    if city1_id:
        data = {
            'city1_id': city1_id,
            'address1_id': adress1_id,
            'city_inside2': cities,
        }
        return data
    else:
        data = {
            'city1_id': another_id,
            'address1_id': adress1_id,
            'city_inside2': cities,
        }
        return data


async def getter_another_outside1(dialog_manager: DialogManager, **kwargs):
    another_outside1 = await get_cities_outside()
    data = {
        'another_outside1': [(city.city_name, city.id) for city in another_outside1],
    }
    return data

async def getter_another_outside2(dialog_manager: DialogManager, **kwargs):
    another_outside2 = await get_cities_outside()
    data = {
        'another_outside2': [(city.city_name, city.id) for city in another_outside2],
    }
    return data


async def get_order(dialog_manager: DialogManager, **kwargs):
    topics = [
        ("Туда-обратно", '1'),
    ]
    adress1_id = dialog_manager.dialog_data.get('address1_id')
    adress2_id = dialog_manager.dialog_data.get('address2_id')

    city1_id = dialog_manager.dialog_data.get('city1_id')
    city2_id = dialog_manager.dialog_data.get('city2_id')
    another1_id = dialog_manager.dialog_data.get('another1_id')
    another2_id = dialog_manager.dialog_data.get('another2_id')

    price = 0

    selected_items = dialog_manager.dialog_data.get('selected_items', set())

    if city1_id and city2_id:
        # связка изменние цены индивидуально
        price = await get_route_price(city1_id, city2_id)
        # Бесплатные поездки
        # user_id = await get_user(dialog_manager.event.from_user.id)
        # if user_id.free_ride == 0:
        #     price = 0

    elif another1_id or another2_id:
        price1 = 0
        price2 = 0
        if another1_id is not None:
            another1_id_obj = await get_cities_outside_name(another1_id)
            price1 = another1_id_obj.price
            city1_id = another1_id_obj.city_name
        if another2_id is not None:
            another2_id_obj = await get_cities_outside_name(another2_id)
            price2 = another2_id_obj.price
            city2_id = another2_id_obj.city_name

        price += max(int(price1), int(price2))


    if selected_items:
        for item_id in selected_items:
            price = update_price(price, selected_items, item_id)


        selected_items_display = ', '.join(
            name for name, id in topics if id in selected_items)
        dialog_manager.dialog_data['price'] = price
        dialog_manager.dialog_data['add_address'] = selected_items_display
        data = {
            'city1_id': city1_id,
            'city2_id': city2_id,
            'address1_id': adress1_id,
            'address2_id': adress2_id,
            'price': price,
            'add_address': selected_items_display,
            'topics': topics,
            'first_show': True,
        }
        return data

    dialog_manager.dialog_data['price'] = price
    data = {
        'city1_id': city1_id,
        'city2_id': city2_id,
        'address1_id': adress1_id,
        'address2_id': adress2_id,
        'price': price,
        'topics': topics,
        'first_show': False,
    }
    return data
