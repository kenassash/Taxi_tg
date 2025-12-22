import os
import re

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv

from app.database.requests import get_all_orders, get_driver, delete_order_execution, delete_order_pass, \
    get_order_driver, get_user, set_order, shop_order_add, set_chat_id_driver, set_chat_id_user, get_settings, \
    get_next_available_driver, increment_driver_order_count, check_and_reset_if_needed, mark_driver_inactive
from filters.chat_type import ChatTypeFilter
import app.keyboards as kb
import app.kb.kb_shop as kb_sh

shop_router = Router()
shop_router.message.filter(ChatTypeFilter(['private']))
load_dotenv()


@shop_router.callback_query(F.data == 'shoporder')
async def shop_add_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer('')
    await callback.message.edit_text(f"Выберите ценну или куда поедите",
                                     reply_markup=await kb_sh.shop_price())


@shop_router.callback_query(F.data.startswith('shopprice_'))
async def shop_price(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer('')
    user_id = await get_user(callback.from_user.id)
    price = callback.data.split('_')[1]
    data = {
        'city1_id': user_id.shop_name,
        'city2_id': user_id.shop_name,
        'address1_id': 'доставка',
        'address2_id': 'доставка',

        'price': int(price)
    }
    order_id = await set_order(user_id.id, data)
    order_data = await get_all_orders(order_id)
    message_id = None

    sent_driver_message = await callback.message.edit_text(f"<b>Ожидайте водителя⌛</b>",
                                                           reply_markup=await kb.delete_order(order_id))

    auto_distribution = await get_settings()
    if auto_distribution and auto_distribution.auto_distribution:
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
            sent_message = await bot.send_message(
                chat_id=next_driver.tg_id,
                text=f"<b>{user_id.shop_name}</b>' доставка!\n"
                     f"Цена: <b>{price}Р</b>",
                reply_markup=await kb.accept_or_skip(order_id)
            )
            await increment_driver_order_count(next_driver.tg_id)
            await set_chat_id_driver(order_data.id, sent_driver_message.message_id)
            await set_chat_id_user(order_data.id, driver_id=str(next_driver.tg_id), chat_id_driver=str(sent_message.message_id))
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
            admin_list = bot.my_admins_list if hasattr(bot, 'my_admins_list') else []
            for admin_id in admin_list:
                try:
                    admin_message = await bot.send_message(
                        chat_id=admin_id,
                        text=f"📋 <b>Новый заказ доставки (автораспределение)</b>\n\n"
                             f"<b>{user_id.shop_name}</b>' доставка!\n"
                             f"Цена: <b>{price}Р</b>\n\n"
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
            await set_chat_id_user(order_data.id, admin_messages=admin_messages_dict)
    else:
        # Автораспределение выключено - отправляем в группу
        sent_message = await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                              text=f"<b>{user_id.shop_name}</b>' доставка!\n"
                                                   f"Цена: <b>{price}Р</b>",
                                              reply_markup=await kb.accept(order_id))
        await set_chat_id_driver(order_data.id, sent_driver_message.message_id)
        await set_chat_id_user(order_data.id, chat_id_driver=str(sent_message.message_id))
    await state.clear()
    # await state.update_data(message_id=sent_message.message_id)


class ShopPointend(StatesGroup):
    send_pont_end = State()
    price_shop = State()


@shop_router.callback_query(F.data == 'shop_point_end')
async def shop_add_point(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await callback.answer('')
    await callback.message.edit_text(f"Напишите куда доставка",
                                     reply_markup=await kb.cancel_order())
    await state.set_state(ShopPointend.send_pont_end)


@shop_router.message(ShopPointend.send_pont_end, F.text)
async def shop_point_end_addres(message: Message, state: FSMContext):
    if message.text:
        await state.update_data(address2_id=message.text)
        await message.answer(f'Введите сумму за доставку')
        await state.set_state(ShopPointend.price_shop)
    else:
        await message.answer('Вы ввели не корретно адрес')


@shop_router.message(ShopPointend.price_shop, F.text)
async def shop_point_end_addres(message: Message, state: FSMContext, bot: Bot):
    input_int = message.text.strip()
    pattern = r"^\d+$"
    if re.match(pattern, input_int):
        await state.update_data(price=int(input_int))
        data = await state.get_data()
        user_id = await get_user(message.from_user.id)
        data.update({'city1_id': user_id.shop_name,
                     'city2_id': user_id.shop_name,
                     'address1_id': 'Доставка'})
        user_id = await get_user(message.from_user.id)
        order_id = await set_order(user_id.id, data)
        message_id = None
        sent_driver_message = await message.answer(f"<b>Ожидайте водителя⌛</b>",
                                                   reply_markup=await kb.delete_order(order_id))
        
        auto_distribution = await get_settings()
        if auto_distribution and auto_distribution.auto_distribution:
            # Автораспределение включено - отправляем водителю
            await check_and_reset_if_needed()
            next_driver = await get_next_available_driver()
            
            if not next_driver:
                await message.answer("В данный момент нет свободных водителей.")
                return
            
            try:
                sent_message = await bot.send_message(
                    chat_id=next_driver.tg_id,
                    text=f"<b>{user_id.shop_name}</b>' доставка!\n"
                         f"Конечная точка: <b>{data['address2_id']}</b>\n\n"
                         f"Цена: <b>{data['price']}Р</b>",
                    reply_markup=await kb.accept_or_skip(order_id)
                )
                await increment_driver_order_count(next_driver.tg_id)
                await set_chat_id_driver(order_id, sent_driver_message.message_id)
                await set_chat_id_user(order_id, driver_id=str(next_driver.tg_id), chat_id_driver=str(sent_message.message_id))
            except TelegramBadRequest as e:
                if "chat not found" in str(e).lower():
                    await mark_driver_inactive(next_driver.tg_id)
                    await message.answer("Водитель недоступен. Попробуйте позже.")
                    return
                else:
                    raise e
            
            # Отправляем заказ админам для мониторинга
            admin_messages_dict = {}
            try:
                admin_list = bot.my_admins_list if hasattr(bot, 'my_admins_list') else []
                for admin_id in admin_list:
                    try:
                        admin_message = await bot.send_message(
                            chat_id=admin_id,
                            text=f"📋 <b>Новый заказ доставки (автораспределение)</b>\n\n"
                                 f"👤 <b>Водитель:</b> {next_driver.name}\n"
                                 f"📞 <b>Телефон:</b> {next_driver.phone}\n"
                                 f"🚕 <b>Автомобиль:</b> {next_driver.car_name}\n\n"
                                 f"<b>{user_id.shop_name}</b>' доставка!\n"
                                 f"Конечная точка: <b>{data['address2_id']}</b>\n\n"
                                 f"Цена: <b>{data['price']}Р</b>",
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
            sent_message = await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                  text=f"<b>{user_id.shop_name}</b>' доставка!\n"
                                                       f"Конечная точка: <b>{data['address2_id']}</b>\n\n"
                                                       f"Цена: <b>{data['price']}Р</b>",
                                                  reply_markup=await kb.accept(order_id))
            await set_chat_id_driver(order_id, sent_driver_message.message_id)
            await set_chat_id_user(order_id, chat_id_driver=str(sent_message.message_id))

        await state.clear()
        # await state.update_data(message_id=sent_message.message_id)
    else:
        await message.answer("Пожалуйста, введите только цифры.") 
