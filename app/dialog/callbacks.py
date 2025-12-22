import os

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, Multiselect, Select, ManagedMultiselect, ManagedRadio, Radio

from app.database.requests import (
    get_all_orders,
    get_cities_inside_test,
    get_cities_inside_id,
    get_user,
    set_order,
    set_chat_id_user,
    up_price_passager, get_least_loaded_driver, update_users, get_settings, get_all_active_drivers,
    get_next_available_driver, increment_driver_order_count, check_and_reset_if_needed, mark_driver_inactive,
    update_driver
)
from app.dialog.states import AddOrder, StartOrder
import app.keyboards as kb


async def back_in_start(callback: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    await dialog_manager.start(AddOrder.city1, mode=StartMode.RESET_STACK)

async def get_info_by_driver_handler(
        callback: CallbackQuery,
        _: Button,
        manager: DialogManager
) -> None:
    bot: Bot = manager.middleware_data["bot"]

    driver = manager.dialog_data["driver_info"]
    settings = await get_settings()
    auto_distribution = settings.auto_distribution if settings else False
    
    text_driver = f"Здравствуйте, {driver.name}\n\n"
    text_driver += f"<b>Автомобиль: </b>{driver.car_name}, {driver.number_car}\n"
    
    # Показываем статус только если автораспределение включено
    if auto_distribution:
        status_text = ["🔴 Не на линии", "🟢 На линии"][driver.active]
        text_driver += f"<b>Статус: </b>{status_text}\n"
    
    text_driver += f"<b>Телефон: </b>{driver.phone}\n"
    text_driver += f"<b>Баланс</b> {driver.price}"
    
    await bot.send_photo(
        chat_id=callback.from_user.id,
        photo=driver.photo_car,
        caption=text_driver
    )

async def on_paid_free_selected(
    callback: CallbackQuery,
    widget: ManagedRadio,
    dialog_manager: DialogManager,
    item_id: str
):
    dialog_manager.dialog_data["paid_free_selected"] = True
    await update_users(dialog_manager.event.from_user.id, paid_free_value=str(item_id))
    await dialog_manager.switch_to(StartOrder.user)


async def on_driver_status_changed(
        callback: CallbackQuery,
        widget: Radio,
        dialog_manager: DialogManager,
        item_id: str
):
    """Обработчик изменения статуса водителя"""
    from app.driver_activity_check import update_driver_last_interaction
    
    driver_id = callback.from_user.id

    # Обновляем статус водителя в базе
    if item_id == 'active':
        await update_driver(driver_id, active=True)
        # Устанавливаем время последнего взаимодействия при активации
        update_driver_last_interaction(driver_id)
        await callback.answer("Водитель активирован!")
    elif item_id == 'inactive':
        await update_driver(driver_id, active=False)
        await callback.answer("Водитель деактивирован!")

    # Обновляем данные в dialog_manager
    dialog_manager.dialog_data["driver_status_changed"] = True

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



async def cancel_upprice(callback: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    await callback.message.delete()
    order_id_id = dialog_manager.dialog_data.get('order_id')
    order_data = await get_all_orders(order_id_id)
    auto_distribution = await get_settings()
    if auto_distribution.auto_distribution:
        await dialog_manager.event.bot.edit_message_text(chat_id=order_data.driver_id,
                                                         message_id=order_data.chat_id_driver,
                                                         text=f"<b>❌Пассажир отменил заказ</b>\n\n"
                                                              f"Телефон <b>{order_data.user_rel.phone}</b>")
    else:
        await dialog_manager.event.bot.edit_message_text(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                         message_id=order_data.chat_id_driver,
                                                         text=f"<b>❌Пассажир отменил заказ</b>\n\n"
                                                              f"Телефон <b>{order_data.user_rel.phone}</b>")
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
    bot: Bot = dialog_manager.middleware_data["bot"]
    state: FSMContext = dialog_manager.middleware_data["state"]

    # dialog_manager = BgManager(user=user, chat=chat, bot=<bot>, router=<router>, intent_id=None, stack_id="")
    bg = dialog_manager.bg(None, os.getenv('CHAT_GROUP_ID'))
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

    auto_distribution = await get_settings()
    if auto_distribution.auto_distribution:
        # Проверяем, нужно ли сбросить статусы заказов
        await check_and_reset_if_needed()
        
        # Ищем водителя с достаточным балансом
        max_attempts = 10  # Ограничиваем количество попыток
        attempts = 0
        next_driver = None
        
        while attempts < max_attempts:
            # Получаем следующего доступного водителя по статусу заказа
            next_driver = await get_next_available_driver()
            
            if not next_driver:
                await callback.answer(
                    "В данный момент нет свободных водителей.",
                    show_alert=True
                )
                return
            
            # Проверяем баланс водителя перед отправкой заказа
            if next_driver.price <= 0:
                # Помечаем водителя как неактивного и сбрасываем счетчик
                await mark_driver_inactive(next_driver.tg_id)
                from app.database.requests import async_session
                from app.database.models import Driver
                from sqlalchemy import update
                async with async_session() as session:
                    await session.execute(
                        update(Driver)
                        .where(Driver.tg_id == next_driver.tg_id)
                        .values(order_count=False)
                    )
                    await session.commit()
                
                attempts += 1
                continue  # Ищем следующего водителя
            
            # Нашли водителя с достаточным балансом
            break
        
        if not next_driver or next_driver.price <= 0:
            await callback.answer(
                "В данный момент нет доступных водителей с достаточным балансом.",
                show_alert=True
            )
            return

        # Сначала отправляем заказ админам для мониторинга
        admin_messages_dict = {}
        try:
            admin_list = bot.my_admins_list if hasattr(bot, 'my_admins_list') else []
            for admin_id in admin_list:
                try:
                    admin_message = await bot.send_message(
                        chat_id=admin_id,
                        text=f"📋 <b>Новый заказ (автораспределение)</b>\n\n"
                             f"{text_order}\n\n"
                             f"👤 <b>Водитель:</b> {next_driver.name}\n"
                             f"📞 <b>Телефон:</b> {next_driver.phone}\n"
                             f"🚕 <b>Автомобиль:</b> {next_driver.car_name}",
                        reply_markup=await kb.accept(order_id)
                    )
                    admin_messages_dict[str(admin_id)] = admin_message.message_id
                except TelegramBadRequest as e:
                    pass
        except Exception as e:
            pass
        
        # Потом отправляем заказ водителю
        try:
            message_id_driver = await bot.send_message(
                chat_id=next_driver.tg_id,  
                text=text_order,
                reply_markup=await kb.accept_or_skip(order_id)
            )
            
            # Помечаем водителя как получившего заказ
            await increment_driver_order_count(next_driver.tg_id)
            
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                # Помечаем водителя как неактивного
                await mark_driver_inactive(next_driver.tg_id)
                await callback.answer(
                    "Водитель недоступен. Попробуйте позже.",
                    show_alert=True
                )
                return
            else:
                raise e

        # Сохраняем в базу
        await set_chat_id_user(order_id, driver_id=str(next_driver.tg_id), chat_id_driver=str(message_id_driver.message_id))
        
        # Сохраняем message_id админов в базу
        if admin_messages_dict:
            await set_chat_id_user(order_id, admin_messages=admin_messages_dict)
    else:
        dialog_manager.dialog_data.clear()
        dialog_manager.dialog_data['order_id'] = order_id
        # await bg.start(data=data_test, mode=StartMode.NORMAL, state=AddOrder.upprice)
        test = await get_least_loaded_driver()
        message_id_driver = await dialog_manager.event.bot.send_message(
            chat_id=os.getenv('CHAT_GROUP_ID'),
            text=text_order,
            reply_markup=await kb.accept(order_id)

        )
        await set_chat_id_user(order_id, chat_id_driver=str(message_id_driver.message_id))

    # Очищаем dialog_data, но сохраняем контекст
    dialog_manager.dialog_data.clear()
    dialog_manager.dialog_data['order_id'] = order_id
    # dialog_manager.dialog_data['add_address'] = order_data.add_address
    # запись в бд massage_id
    # await set_chat_id_user(order_id, chat_id_driver=str(message_id_driver.message_id))
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
    auto_distribution = await get_settings()
    if auto_distribution.auto_distribution:
        await dialog_manager.event.bot.edit_message_text(chat_id=order_id.driver_id,
                                                         message_id=order_id.chat_id_driver,
                                                         text=text_order,
                                                         reply_markup=await kb.accept(order_id.id))
    else:
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

    auto_distribution = await get_settings()
    if auto_distribution.auto_distribution:
        # Автораспределение включено - отправляем водителю
        await check_and_reset_if_needed()
        next_driver = await get_next_available_driver()
        
        if not next_driver:
            await callback.answer(
                "В данный момент нет свободных водителей.",
                show_alert=True
            )
            return
        
        try:
            message_id_driver = await dialog_manager.event.bot.send_message(
                chat_id=next_driver.tg_id,
                text=text_order,
                reply_markup=await kb.accept_or_skip(order_id)
            )
            await increment_driver_order_count(next_driver.tg_id)
            await set_chat_id_user(order_id, driver_id=str(next_driver.tg_id), chat_id_driver=str(message_id_driver.message_id))
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                await mark_driver_inactive(next_driver.tg_id)
                await callback.answer(
                    "Водитель недоступен. Попробуйте позже.",
                    show_alert=True
                )
                return
            else:
                raise e
        
        # Отправляем заказ админам для мониторинга
        admin_messages_dict = {}
        try:
            admin_list = dialog_manager.event.bot.my_admins_list if hasattr(dialog_manager.event.bot, 'my_admins_list') else []
            for admin_id in admin_list:
                try:
                    admin_message = await dialog_manager.event.bot.send_message(
                        chat_id=admin_id,
                        text=f"📋 <b>Новый заказ (автораспределение)</b>\n\n"
                             f"{text_order}\n\n"
                             f"👤 <b>Водитель:</b> {next_driver.name}\n"
                             f"📞 <b>Телефон:</b> {next_driver.phone}\n"
                             f"🚕 <b>Автомобиль:</b> {next_driver.car_name}",
                        reply_markup=await kb.accept(order_id)
                    )
                    admin_messages_dict[str(admin_id)] = admin_message.message_id
                except TelegramBadRequest as e:
                    pass
        except Exception as e:
            pass
        
        # Сохраняем message_id админов в базу
        if admin_messages_dict:
            await set_chat_id_user(order_id, admin_messages=admin_messages_dict)
    else:
        # Автораспределение выключено - отправляем в группу
        message_id_driver = await dialog_manager.event.bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                                        text=text_order,
                                                                        reply_markup=await kb.accept(order_id))
        await set_chat_id_user(order_id, chat_id_driver=str(message_id_driver.message_id))
    
    # Очищаем dialog_data, но сохраняем контекст
    dialog_manager.dialog_data.clear()
    dialog_manager.dialog_data['order_id'] = order_id
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

    auto_distribution = await get_settings()
    if auto_distribution.auto_distribution:
        # Автораспределение включено - отправляем водителю
        await check_and_reset_if_needed()
        next_driver = await get_next_available_driver()
        
        if not next_driver:
            await callback.answer(
                "В данный момент нет свободных водителей.",
                show_alert=True
            )
            return
        
        try:
            message_id_driver = await dialog_manager.event.bot.send_message(
                chat_id=next_driver.tg_id,
                text=text_order,
                reply_markup=await kb.accept_or_skip(order_id)
            )
            await increment_driver_order_count(next_driver.tg_id)
            await set_chat_id_user(order_id, driver_id=str(next_driver.tg_id), chat_id_driver=str(message_id_driver.message_id))
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                await mark_driver_inactive(next_driver.tg_id)
                await callback.answer(
                    "Водитель недоступен. Попробуйте позже.",
                    show_alert=True
                )
                return
            else:
                raise e
        
        # Отправляем заказ админам для мониторинга
        admin_messages_dict = {}
        try:
            admin_list = dialog_manager.event.bot.my_admins_list if hasattr(dialog_manager.event.bot, 'my_admins_list') else []
            for admin_id in admin_list:
                try:
                    admin_message = await dialog_manager.event.bot.send_message(
                        chat_id=admin_id,
                        text=f"📋 <b>Новый заказ (автораспределение)</b>\n\n"
                             f"{text_order}\n\n"
                             f"👤 <b>Водитель:</b> {next_driver.name}\n"
                             f"📞 <b>Телефон:</b> {next_driver.phone}\n"
                             f"🚕 <b>Автомобиль:</b> {next_driver.car_name}",
                        reply_markup=await kb.accept(order_id)
                    )
                    admin_messages_dict[str(admin_id)] = admin_message.message_id
                except TelegramBadRequest as e:
                    pass
        except Exception as e:
            pass
        
        # Сохраняем message_id админов в базу
        if admin_messages_dict:
            await set_chat_id_user(order_id, admin_messages=admin_messages_dict)
    else:
        # Автораспределение выключено - отправляем в группу
        message_id_driver = await dialog_manager.event.bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                                        text=text_order,
                                                                        reply_markup=await kb.accept(order_id))
        await set_chat_id_user(order_id, chat_id_driver=str(message_id_driver.message_id))
    # Очищаем dialog_data, но сохраняем контекст
    dialog_manager.dialog_data.clear()
    dialog_manager.dialog_data['order_id'] = order_id
    await dialog_manager.switch_to(state=AddOrder.upprice)
