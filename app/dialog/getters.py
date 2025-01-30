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
    data = {
        "city1_id": order_data.city1_id,
        "city2_id": order_data.city2_id,
        "address1_id": order_data.address1_id,
        "address2_id": order_data.address2_id,
        # "add_address": dialog_manager.dialog_data.get('add_address'),
        # "price": order_data.price,
        # 'first_show': True,
    }
    if order_data.add_address:
        data["add_address"] = order_data.add_address
        data["first_show"] = True
    if order_data.add_new_address1:
        data["add_new_address1"] = order_data.add_new_address1
        data["add_street_address1"] = order_data.add_street_address1
        data["getter_new_address1"] = True
    if order_data.add_new_address2:
        data["add_new_address2"] = order_data.add_new_address2
        data["add_street_address2"] = order_data.add_street_address2
        data["getter_new_address2"] = True
    # Добавляем цену
    data["price"] = order_data.price

    return data
    # if dialog_manager.dialog_data.get('add_address'):
    #     data = {
    #         "city1_id": order_data.city1_id,
    #         "city2_id": order_data.city2_id,
    #         "address1_id": order_data.address1_id,
    #         "address2_id": order_data.address2_id,
    #         "add_address": dialog_manager.dialog_data.get('add_address'),
    #         "price": order_data.price,
    #         'first_show': True,
    #     }
    #     return data
    #
    # data = {
    #     "city1_id": order_data.city1_id,
    #     "city2_id": order_data.city2_id,
    #     "address1_id": order_data.address1_id,
    #     "address2_id": order_data.address2_id,
    #     "price": order_data.price,
    #     'first_show': False,
    # }
    # return data


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


async def add_new_address_getter(dialog_manager: DialogManager, **kwargs, ):
    cities = await get_cities_inside()
    data = {
        'new_address1': cities,
    }
    return data

async def add_new_address_getter2(dialog_manager: DialogManager, **kwargs, ):
    cities = await get_cities_inside()
    data = {
        'new_address2': cities,
    }
    return data


async def getter_another_outside1(dialog_manager: DialogManager, **kwargs):
    another_outside1 = await get_cities_outside()
    data = {
        'another_outside1': sorted(
            [(city.city_name, city.id) for city in another_outside1],
            key=lambda x: x[0]  # Сортируем по названию города
        ),
    }
    return data


async def getter_another_outside2(dialog_manager: DialogManager, **kwargs):
    another_outside2 = await get_cities_outside()
    data = {
        'another_outside2': sorted(
            [(city.city_name, city.id) for city in another_outside2],
            key=lambda x: x[0]  # Сортируем по названию города
        ),
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

    selected_items = dialog_manager.dialog_data.get('selected_items')

    price = 0
    price_route = 0
    data_hide = {}
    user_id = await get_user(dialog_manager.event.from_user.id)
    if city1_id and city2_id:
        # связка изменние цены индивидуально
        price = await get_route_price(city1_id, city2_id)
        data_hide = {'another_hide': True}
        # Бесплатные поездки
        if user_id.free_ride == 0:
            price_route += price
            price = 0

    elif another1_id or another2_id:
        # скрыть кнопку "Добавить адрес" если есть другой н.п.
        data_hide = {'another_hide': False}
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
        # цена умножается
        price *= 2
        # Бесплатные поездки
        if user_id.free_ride == 0:
            price = price_route
        # Выведет: "Туда-обратно"
        dialog_manager.dialog_data['add_address'] = topics[0][0]
        dialog_manager.dialog_data['price'] = price

        data = {
            'city1_id': city1_id,
            'city2_id': city2_id,
            'address1_id': adress1_id,
            'address2_id': adress2_id,
            'price': price,
            'topics': topics,
            'first_show': True,
        }
        print(dialog_manager.dialog_data)
        return data

    dialog_manager.dialog_data['price'] = price
    dialog_manager.dialog_data.pop('add_address', None)
    data = {
        'city1_id': city1_id,
        'city2_id': city2_id,
        'address1_id': adress1_id,
        'address2_id': adress2_id,
        'price': price,
        'topics': topics,
        'first_show': False,
    }
    if data_hide:
        data.update(data_hide)
    print(dialog_manager.dialog_data)
    return data


async def get_order_with_new_address1(dialog_manager: DialogManager, **kwargs):
    city1_id = dialog_manager.dialog_data.get('city1_id')
    adress1_id = dialog_manager.dialog_data.get('address1_id')

    city2_id = dialog_manager.dialog_data.get('city2_id')
    adress2_id = dialog_manager.dialog_data.get('address2_id')

    add_new_address1 = dialog_manager.dialog_data.get('add_new_address1')
    add_street_address1 = dialog_manager.dialog_data.get('add_street_address1')

    price_old = dialog_manager.dialog_data.get('price')
    price_new = await get_route_price(city2_id, add_new_address1)
    price = price_old + price_new
    # удаляем старую ценну добавляем новую
    dialog_manager.dialog_data['price'] = price

    data = {
        'city1_id': city1_id,
        'city2_id': city2_id,
        'address1_id': adress1_id,
        'address2_id': adress2_id,
        'add_new_address1': add_new_address1,
        'add_street_address1': add_street_address1,
        'price': price,
    }
    return data

async def get_order_with_new_address2(dialog_manager: DialogManager, **kwargs):
    city1_id = dialog_manager.dialog_data.get('city1_id')
    adress1_id = dialog_manager.dialog_data.get('address1_id')

    city2_id = dialog_manager.dialog_data.get('city2_id')
    adress2_id = dialog_manager.dialog_data.get('address2_id')

    add_new_address1 = dialog_manager.dialog_data.get('add_new_address1')
    add_street_address1 = dialog_manager.dialog_data.get('add_street_address1')

    add_new_address2 = dialog_manager.dialog_data.get('add_new_address2')
    add_street_address2 = dialog_manager.dialog_data.get('add_street_address2')

    price_old = dialog_manager.dialog_data.get('price')
    price_new = await get_route_price(add_new_address1, add_new_address2)
    price = price_old + price_new
    # удаляем старую ценну добавляем новую
    dialog_manager.dialog_data['price'] = price

    print(dialog_manager.dialog_data)

    data = {
        'city1_id': city1_id,
        'city2_id': city2_id,
        'address1_id': adress1_id,
        'address2_id': adress2_id,
        'add_new_address1': add_new_address1,
        'add_street_address1': add_street_address1,
        'add_new_address2': add_new_address2,
        'add_street_address2': add_street_address2,
        'price': price,
    }
    return data