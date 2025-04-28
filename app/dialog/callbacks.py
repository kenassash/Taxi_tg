import os

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, Multiselect, Select, ManagedMultiselect

from app.database.requests import (
    get_all_orders,
    get_cities_inside_test,
    get_cities_inside_id,
    get_user,
    set_order,
    set_chat_id_user,
    up_price_passager, get_least_loaded_driver
)
from app.dialog.states import AddOrder
import app.keyboards as kb


async def back_in_start(callback: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    await dialog_manager.start(AddOrder.city1, mode=StartMode.RESET_STACK)


async def cancel_in_start(callback: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    await callback.message.delete()
    await callback.message.answer('Вы отменили. Нажмите /start что бы продолжить')


async def commit(event: CallbackQuery,
                 checkbox: ManagedMultiselect,
                 dialog_manager: DialogManager,
                 item_id: str):
    selected_items = checkbox.get_checked()
    dialog_manager.dialog_data['selected_items'] = selected_items
    if not dialog_manager.dialog_data['selected_items']:
        dialog_manager.dialog_data.pop('selected_items', None)

    # # Получаем список выбранных элементов
    # selected_items = dialog_manager.dialog_data.get('selected_items', set())
    #
    # # Проверяем, выбран ли уже элемент
    # if item_id in selected_items:
    #     # Если элемент уже выбран, убираем его
    #     selected_items.remove(item_id)
    # else:
    #     # Если элемент не выбран, добавляем его
    #     selected_items.add(item_id)
    #
    # # Сохраняем обновленный список выбранных элементов в dialog_data
    # if not selected_items:
    #     dialog_manager.dialog_data.pop('selected_items', None)
    # else:
    #     # Иначе, сохраняем обновленный список выбранных элементов в dialog_data
    #     dialog_manager.dialog_data['selected_items'] = selected_items


async def cancel_upprice(callback: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    await callback.message.delete()
    order_id_id = dialog_manager.dialog_data.get('order_id')
    order_data = await get_all_orders(order_id_id)
    await dialog_manager.event.bot.edit_message_text(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                     message_id=order_data.chat_id_driver,
                                                     text=f"<b>❌Пассажир отменил заказ</b>\n\n"
                                                          # f"Заказ <b>{order_data.id}</b>\n\n"
                                                          f"Телефон <b>{order_data.user_rel.phone}</b>")
                                                          # f"Начальная точка: <b>{order_data.city1_id} - {order_data.address1_id}</b>\n\n"
                                                          # f"Конечная точка: <b>{order_data.city2_id} - {order_data.address2_id}</b>\n\n"
                                                          # f"Цена: <b>{order_data.price}Р</b>\n\n")

    await dialog_manager.event.message.answer('Вы отменили. Нажмите /start что бы продолжить')


async def on_choosen_city1(callback: CallbackQuery,
                           widget: Select,
                           dialog_manager: DialogManager,
                           city1_id: str):
    city1_id = await get_cities_inside_test(city1_id)
    dialog_manager.dialog_data['city1_id'] = city1_id.city_name
    await dialog_manager.switch_to(AddOrder.address1)


async def on_choosen_city2(callback: CallbackQuery,
                           widget: Select,
                           dialog_manager: DialogManager,
                           city2_id: str):
    dialog_manager.dialog_data.pop('another2_id', None)
    city2_id = await get_cities_inside_test(city2_id)
    dialog_manager.dialog_data['city2_id'] = city2_id.city_name
    await dialog_manager.switch_to(AddOrder.address2)
async def add_new_address_cb(callback: CallbackQuery,
                           widget: Select,
                           dialog_manager: DialogManager,
                           add_new_address1: str):
    add_new_address1 = await get_cities_inside_test(add_new_address1)
    dialog_manager.dialog_data['add_new_address1'] = add_new_address1.city_name
    await dialog_manager.switch_to(AddOrder.add_street_address1)

async def add_new_address_cb2(callback: CallbackQuery,
                           widget: Select,
                           dialog_manager: DialogManager,
                           add_new_address2: str):
    add_new_address2 = await get_cities_inside_test(add_new_address2)
    dialog_manager.dialog_data['add_new_address2'] = add_new_address2.city_name
    await dialog_manager.switch_to(AddOrder.add_street_address2)


async def on_choosen_adress1(message: Message,
                             widget: ManagedTextInput,
                             dialog_manager: DialogManager,
                             adress1: str):
    dialog_manager.dialog_data['address1_id'] = message.text
    await dialog_manager.switch_to(AddOrder.city2)


async def on_choosen_adress2(message: Message,
                             widget: ManagedTextInput,
                             dialog_manager: DialogManager,
                             adress1: str):
    dialog_manager.dialog_data['address2_id'] = message.text
    await dialog_manager.switch_to(AddOrder.order_start)

async def on_choosen_add_address_cb(message: Message,
                             widget: ManagedTextInput,
                             dialog_manager: DialogManager,
                             add_street_address1: str):
    dialog_manager.dialog_data['add_street_address1'] = message.text
    await dialog_manager.switch_to(AddOrder.order_start_with_new_address1)

async def on_choosen_add_address_cb2(message: Message,
                             widget: ManagedTextInput,
                             dialog_manager: DialogManager,
                             add_street_address2: str):
    dialog_manager.dialog_data['add_street_address2'] = message.text
    await dialog_manager.switch_to(AddOrder.order_start_with_new_address2)

async def on_choosen_another1(callback: CallbackQuery,
                              widget: Select,
                              dialog_manager: DialogManager,
                              another1_id: str):
    dialog_manager.dialog_data.pop('city1_id', None)
    another1_id = await get_cities_inside_id(another1_id)
    dialog_manager.dialog_data['another1_id'] = another1_id.city_name
    await dialog_manager.switch_to(AddOrder.address1)


async def on_choosen_another2(callback: CallbackQuery,
                              widget: Select,
                              dialog_manager: DialogManager,
                              another2_id: str):
    dialog_manager.dialog_data.pop('city2_id', None)
    another2_id = await get_cities_inside_id(another2_id)
    dialog_manager.dialog_data['another2_id'] = another2_id.city_name
    await dialog_manager.switch_to(AddOrder.address2)


async def on_choosen_another_state(callback: CallbackQuery,
                                   widget: Button,
                                   dialog_manager: DialogManager):
    await dialog_manager.switch_to(AddOrder.another1)


async def on_choosen_another_state2(callback: CallbackQuery,
                                    widget: Button,
                                    dialog_manager: DialogManager):
    await dialog_manager.switch_to(AddOrder.another2)


async def order_now(callback: CallbackQuery,
                    widget: Button,
                    dialog_manager: DialogManager):
    # dialog_manager = BgManager(user=user, chat=chat, bot=<bot>, router=<router>, intent_id=None, stack_id="")
    # bg = dialog_manager.bg(None, os.getenv('CHAT_GROUP_ID'))
    another1_id = dialog_manager.dialog_data.get('another1_id')
    another2_id = dialog_manager.dialog_data.get('another2_id')
    if another1_id is not None:
        dialog_manager.dialog_data['city1_id'] = another1_id
        dialog_manager.dialog_data.pop('another1_id', None)
    if another2_id is not None:
        dialog_manager.dialog_data['city2_id'] = another2_id
        dialog_manager.dialog_data.pop('another2_id', None)
    dialog_manager.dialog_data.pop('selected_items', None)

    data_test = dialog_manager.dialog_data

    user_id = await get_user(dialog_manager.event.from_user.id)
    order_id = await set_order(user_id.id, data_test)
    topics = [
        ("Туда-обратно", '2'),
    ]
    selected_items = {'1'}
    # Находим значение по ключу
    result = next((name for name, key in topics if key in selected_items), None)

    order_data = await get_all_orders(order_id)
    text_order = (f"🔥Заказ <b>{order_id}</b>🔥\n\n"
                 f"📞Телефон <b>{user_id.phone}</b>\n\n"
                 f"📍:<b>{order_data.city1_id} - {order_data.address1_id.upper()}</b>\n\n"
                 f"️📍:<b>{order_data.city2_id} - {order_data.address2_id.upper()}</b>\n\n")
    if order_data.add_address:
        text_order += f"🔃<b>{order_data.add_address}</b>\n\n"
    text_order += f"Цена: <b>{order_data.price}Р</b>"


    # await bg.start(data=data_test, mode=StartMode.NORMAL, state=AddOrder.upprice)
    await get_least_loaded_driver()
    message_id_driver = await dialog_manager.event.bot.send_message(chat_id=-1002140227413,
                                                                    text=text_order,
                                                                    reply_markup=await kb.accept(order_id))
    #
    # Очищаем dialog_data, но сохраняем контекст
    dialog_manager.dialog_data.clear()
    dialog_manager.dialog_data['order_id'] = order_id
    # dialog_manager.dialog_data['add_address'] = order_data.add_address
    # запись в бд massage_id
    await set_chat_id_user(order_id, message_id_driver.message_id)
    await dialog_manager.switch_to(state=AddOrder.upprice)


async def upprice_order(callback: CallbackQuery,
                        widget: Button,
                        dialog_manager: DialogManager):
    order_id_id = dialog_manager.dialog_data.get('order_id')
    price = 20
    order_id = await up_price_passager(order_id_id, price)
    text_order = (f"🔥Заказ <b>{order_id.id}</b>🔥\n\n"
                 f"📞Телефон <b>{order_id.user_rel.phone}</b>\n\n"
                 f"📍:<b>{order_id.city1_id} - {order_id.address1_id.upper()}</b>\n\n"
                 f"📍:<b>{order_id.city2_id} - {order_id.address2_id.upper()}</b>\n\n")
    if order_id.add_address:
        text_order += f"🔃<b>{order_id.add_address}</b>\n\n"
    if order_id.add_new_address1:
        text_order += f"📍:<b>{order_id.add_new_address1} - {order_id.add_street_address1.upper()}</b>\n\n"
    if order_id.add_new_address2:
        text_order += f"📍:<b>{order_id.add_new_address2} - {order_id.add_street_address2.upper()}</b>\n\n"
    text_order += f"Цена: <b>{order_id.price}Р</b>"

    await dialog_manager.event.bot.edit_message_text(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                     message_id=order_id.chat_id_driver,
                                                     text=text_order,
                                                     reply_markup=await kb.accept(order_id.id))
    await dialog_manager.switch_to(state=AddOrder.upprice)


async def start_order(callback: CallbackQuery,
                      widget: Button,
                      dialog_manager: DialogManager):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.message.answer('Пройдите повторно регистрацию. Нажмите /start')
        return
    await dialog_manager.start(AddOrder.city1, mode=StartMode.RESET_STACK)

async def add_new_address1(callback: CallbackQuery,
                          widget: Button,
                          dialog_manager: DialogManager):
    await dialog_manager.switch_to(AddOrder.add_new_address1, show_mode=ShowMode.EDIT)

async def add_new_address2(callback: CallbackQuery,
                          widget: Button,
                          dialog_manager: DialogManager):
    await dialog_manager.switch_to(AddOrder.add_new_address2, show_mode=ShowMode.EDIT)

async def order_now_with_new_address1(callback: CallbackQuery,
                    widget: Button,
                    dialog_manager: DialogManager):

    data_test = dialog_manager.dialog_data

    user_id = await get_user(dialog_manager.event.from_user.id)
    order_id = await set_order(user_id.id, data_test)

    order_data = await get_all_orders(order_id)
    text_order = (f"🔥Заказ <b>{order_id}</b>🔥\n\n"
                  f"📞Телефон <b>{user_id.phone}</b>\n\n"
                  f"📍:<b>{order_data.city1_id} - {order_data.address1_id.upper()}</b>\n\n"
                  f"️📍:<b>{order_data.city2_id} - {order_data.address2_id.upper()}</b>\n\n"
                  f"️📍:<b>{order_data.add_new_address1} - {order_data.add_street_address1.upper()}</b>\n\n"
                  f"Цена: <b>{order_data.price}Р</b>")

    message_id_driver = await dialog_manager.event.bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                                    text=text_order,
                                                                    reply_markup=await kb.accept(order_id))
    # Очищаем dialog_data, но сохраняем контекст
    dialog_manager.dialog_data.clear()
    dialog_manager.dialog_data['order_id'] = order_id
    # запись в бд massage_id
    await set_chat_id_user(order_id, message_id_driver.message_id)
    await dialog_manager.switch_to(state=AddOrder.upprice)

async def order_now_with_new_address2(callback: CallbackQuery,
                    widget: Button,
                    dialog_manager: DialogManager):

    data_test = dialog_manager.dialog_data

    user_id = await get_user(dialog_manager.event.from_user.id)
    order_id = await set_order(user_id.id, data_test)

    order_data = await get_all_orders(order_id)
    text_order = (f"🔥Заказ <b>{order_id}</b>🔥\n\n"
                  f"📞Телефон <b>{user_id.phone}</b>\n\n"
                  f"📍:<b>{order_data.city1_id} - {order_data.address1_id.upper()}</b>\n\n"
                  f"️📍:<b>{order_data.city2_id} - {order_data.address2_id.upper()}</b>\n\n"
                  f"️📍:<b>{order_data.add_new_address1} - {order_data.add_street_address1.upper()}</b>\n\n"
                  f"️📍:<b>{order_data.add_new_address2} - {order_data.add_street_address2.upper()}</b>\n\n"
                  f"Цена: <b>{order_data.price}Р</b>")

    message_id_driver = await dialog_manager.event.bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                                    text=text_order,
                                                                    reply_markup=await kb.accept(order_id))
    # Очищаем dialog_data, но сохраняем контекст
    dialog_manager.dialog_data.clear()
    dialog_manager.dialog_data['order_id'] = order_id
    # запись в бд massage_id
    await set_chat_id_user(order_id, message_id_driver.message_id)
    await dialog_manager.switch_to(state=AddOrder.upprice)