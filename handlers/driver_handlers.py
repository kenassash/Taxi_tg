import os
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv
from datetime import datetime, timedelta

from app.database.requests import get_all_orders, get_driver, delete_order_execution, delete_order_pass, \
    get_order_driver, save_free_ride, set_chat_id_driver, set_chat_id_user, update_driver
from filters.chat_type import ChatTypeFilter
from app.change_price import Settings
import app.keyboards as kb
import app.kb.kb_shop as kb_sh

driver_router = Router()
driver_router.message.filter(ChatTypeFilter(['private']))
load_dotenv()


@driver_router.callback_query(F.data.startswith('close_'))
async def close(callback: CallbackQuery, bot: Bot):
    try:
        await callback.answer('')
        order_id = await get_all_orders(callback.data.split('_')[1])
        driver_id = await get_driver(callback.from_user.id)
        # message_id = callback.data.split('_')[2]
        message_id = order_id.chat_id_user

        # Удаляем запись запись о начале выполнения заказа
        await delete_order_execution(order_id.id, driver_id.id)
        try:
            # удаляю сообщение у пользователя
            await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id)
        except TelegramBadRequest as e:
            if "message to delete not found" in str(e):
                # Логирование или обработка конкретного случая, если сообщение не найдено
                print("Сообщение уже удалено или не найдено.")
            else:
                raise e
        message_id_pass = await bot.send_message(chat_id=order_id.user_rel.tg_id,
                                                 text=f'<b>Ожидайте ⌛</b>\n'
                                                      f'Будет назначен новый водитель в ближайшее время\n')
        text_order = (f'Водитель {driver_id.name} отменил выпонлнение заказа\n'
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
        message_driver = await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                text=text_order,
                                                reply_markup=await kb.accept(order_id.id))

        await callback.message.edit_text(f'Вы отказались от заказа <b>№{order_id.id}</b>')
        await update_driver(driver_id.tg_id, price=int(driver_id.price + int(driver_id.price * 0.10)))

        await set_chat_id_driver(order_id.id, message_id_pass.message_id)
        await set_chat_id_user(order_id.id, message_driver.message_id)

        await bot.edit_message_reply_markup(
            chat_id=order_id.user_rel.tg_id,
            message_id=message_id_pass.message_id,
            reply_markup=await kb.delete_order(order_id.id))


    except AttributeError:
        await callback.answer('')
        await callback.message.edit_text('Пассажир отменил заказ')


@driver_router.callback_query(F.data.startswith('timewait_'))
async def timewait(callback: CallbackQuery, bot: Bot):
    try:
        await callback.answer('')
        order_id = await get_all_orders(callback.data.split('_')[1])

        driver = await get_driver(callback.from_user.id)
        time_wait = callback.data.split('_')[2]
        # message_id = callback.data.split('_')[3]
        message_id = order_id.chat_id_user
        arrival_time = datetime.now() + timedelta(minutes=float(time_wait))
        formatted_arrival_time = arrival_time.strftime("%H:%M")
        try:
            # удаляю сообщение у пользователя
            await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id)
        except TelegramBadRequest as e:
            if "message to delete not found" in str(e):
                # Логирование или обработка конкретного случая, если сообщение не найдено
                print("Сообщение уже удалено или не найдено.")
            else:
                raise e

        message_pass = await bot.send_photo(chat_id=order_id.user_rel.tg_id,
                                            photo=driver.photo_car,
                                            caption=f'<b>⏳ВРЕМЯ ПРИБЫТИЯ {time_wait} мин</b>\n'
                                                    f'👤{driver.name} на {driver.car_name}\n'
                                                    f'🚕Номер авто: {driver.number_car}\n'
                                                    f'📞Телефон: {driver.phone}\n'
                                                    f'💰Цена поездки: {order_id.price} руб')
        text_driver = (f"🔥Заказ <b>{order_id.id}🔥          ⏳{formatted_arrival_time}⏳</b>\n\n"
                       # f"⏳Время прибытия <b>{formatted_arrival_time} мин</b>\n\n"
                       f"📞Телефон <b>{order_id.user_rel.phone}</b>\n\n"
                       f"📍:<b>{order_id.city1_id} - {order_id.address1_id.upper()}</b>\n\n"
                       f"📍:<b>{order_id.city2_id} - {order_id.address2_id.upper()}</b>\n\n")
        if order_id.add_address:
            text_driver += f"🔃<b>{order_id.add_address}</b>\n\n"
        if order_id.add_new_address1:
            text_driver += f"📍:<b>{order_id.add_new_address1} - {order_id.add_street_address1.upper()}</b>\n\n"
        if order_id.add_new_address2:
            text_driver += f"📍:<b>{order_id.add_new_address2} - {order_id.add_street_address2.upper()}</b>\n\n"
        text_driver += f"Цена: <b>{order_id.price}Р</b>"
        message_driver = await callback.message.edit_text(text=text_driver,
                                                          reply_markup=await kb.on_the_spot_kb(order_id.id,
                                                                                               message_pass.message_id))
        # reply_markup = await kb.close_and_finish(order_id.id)
        await set_chat_id_driver(order_id.id, message_pass.message_id)
        await set_chat_id_user(order_id.id, message_driver.message_id)

        await bot.edit_message_reply_markup(
            chat_id=order_id.user_rel.tg_id,
            message_id=message_pass.message_id,
            reply_markup=await kb.delete_order(order_id.id))
    except AttributeError:
        await callback.answer('')
        await callback.message.answer('Пассажир отменил заказ')


@driver_router.callback_query(F.data.startswith('onthespot_'))
async def on_the_spot(callback: CallbackQuery, bot: Bot):
    try:
        await callback.answer('')
        order_id = await get_all_orders(callback.data.split('_')[1])
        driver = await get_driver(callback.from_user.id)
        # message_id = callback.data.split('_')[2]
        message_id = order_id.chat_id_user
        try:
            # удаляю сообщение у пользователя
            await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id)
        except TelegramBadRequest as e:
            if "message to delete not found" in str(e):
                # Логирование или обработка конкретного случая, если сообщение не найдено
                print("Сообщение уже удалено или не найдено.")
            else:
                raise e

        message_pass = await bot.send_photo(chat_id=order_id.user_rel.tg_id,
                                            photo=driver.photo_car,
                                            caption=f'<b>🎯ВОДИТЕЛЬ ПРИЕХАЛ🎯</b>\n'
                                                    f'👤{driver.name} на {driver.car_name}\n'
                                                    f'🚕Номер авто: {driver.number_car}\n'
                                                    f'📞Телефон: {driver.phone}\n'
                                                    f'💰Цена поездки: {order_id.price} руб')
        text_driver = (f"🔥Заказ <b>{order_id.id}</b>🔥\n\n"
                       f"📞Телефон <b>{order_id.user_rel.phone}</b>\n\n"
                       f"📍:<b>{order_id.city1_id} - {order_id.address1_id.upper()}</b>\n\n"
                       f"📍:<b>{order_id.city2_id} - {order_id.address2_id.upper()}</b>\n\n")
        if order_id.add_address:
            text_driver += f"🔃<b>{order_id.add_address}</b>\n\n"
        if order_id.add_new_address1:
            text_driver += f"📍:<b>{order_id.add_new_address1} - {order_id.add_street_address1.upper()}</b>\n\n"
        if order_id.add_new_address2:
            text_driver += f"📍:<b>{order_id.add_new_address2} - {order_id.add_street_address2.upper()}</b>\n\n"
        text_driver += f"Цена: <b>{order_id.price}Р</b>"
        message_driver = await callback.message.edit_text(text=text_driver,
                                                          reply_markup=await kb.close_and_finish(order_id.id,
                                                                                                 message_pass.message_id))
        await set_chat_id_driver(order_id.id, message_pass.message_id)
        await set_chat_id_user(order_id.id, message_driver.message_id)

        await bot.edit_message_reply_markup(
            chat_id=order_id.user_rel.tg_id,
            message_id=message_pass.message_id,
            reply_markup=await kb.delete_order(order_id.id))
    except AttributeError:
        await callback.answer('')
        await callback.message.answer('Пассажир отменил заказ')


@driver_router.callback_query(F.data.startswith('finish_'))
async def finish(callback: CallbackQuery, bot: Bot):
    try:
        await callback.answer('')
        order_id = await get_all_orders(callback.data.split('_')[1])
        driver_id = await get_driver(callback.from_user.id)
        # message_id_pass = callback.data.split('_')[2]
        message_id_pass = order_id.chat_id_user
        # Проверяем что это был магазин
        # data = order_id.point_start
        # data = order_id.city1_id
        # text = data.split(' ')[0]
        if order_id.user_rel.shop_activate:
            await callback.message.delete()
            try:
                # удаляю сообщение у пользователя
                await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id_pass)
            except TelegramBadRequest as e:
                if "message to delete not found" in str(e):
                    # Логирование или обработка конкретного случая, если сообщение не найдено
                    print("Сообщение уже удалено или не найдено.")
                else:
                    raise e
            await bot.send_message(chat_id=order_id.user_rel.tg_id,
                                   text=f'Заказ выполнен✅.\n',
                                   reply_markup=await kb_sh.shop_order())
            return
        # Удаляем запись запись о начале выполнения заказа
        # await delete_order_execution(order_id.id, driver_id.id)
        # Увеличиваем счетчик поездок
        # Бесплатные поездки
        # user_free_ride = order_id.user_rel.free_ride
        # user_free_ride += 1
        # if user_free_ride == Settings.free_ride:
        #     free_ride_count = 0  # Обнуляем счетчик после 10-й поездки
        #     await save_free_ride(order_id.user_rel.tg_id, free_ride_count)
        #     await bot.send_message(chat_id=order_id.user_rel.tg_id,
        #                            text=f'Поздравляем! Ваша следующая поездка будет бесплатной! 🎉',
        #                            reply_markup=await kb.main())
        # else:
        #     free_ride = user_free_ride
        #     await save_free_ride(order_id.user_rel.tg_id, free_ride)
        #     await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id_pass)
        #     await bot.send_message(chat_id=order_id.user_rel.tg_id,
        #                            text=f'Заказ выполнен✅.\n'
        #                                 f'Спасибо что пользуетесь нашими услугами 🙏\n\n'
        #                                 f'До бесплатной поездки осталось {Settings.free_ride - free_ride}',
        #                            reply_markup=await kb.main())

        # Бесплатные поездки
        user_free_ride = order_id.user_rel.free_ride
        if user_free_ride == 0:
            free_ride = 1
            await save_free_ride(order_id.user_rel.tg_id, free_ride)
        try:
            # удаляю сообщение у пользователя
            await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id_pass)
        except TelegramBadRequest as e:
            if "message to delete not found" in str(e):
                # Логирование или обработка конкретного случая, если сообщение не найдено
                print("Сообщение уже удалено или не найдено.")
            else:
                raise e
        await bot.send_message(chat_id=order_id.user_rel.tg_id,
                               text=f'Заказ выполнен✅.\n'
                                    f'Спасибо что пользуетесь нашими услугами 🙏\n\n',
                               reply_markup=await kb.main())

        await callback.message.delete()
    except AttributeError:
        await callback.answer('')
        await callback.message.answer('Пассажир отменил заказ')


# тестирую личную карточку водителя
@driver_router.message(Command('driver'))
async def driver_lk(message: Message, bot: Bot):
    driver_id = await get_driver(message.from_user.id)
    if driver_id.active:
        status_text = "🟢 На линии"
    else:
        status_text = "🔴 Не на линии"
    text_driver = (f"Здравствуйте, {driver_id.name}\n\n"
                   f"<b>Автомобиль: </b>{driver_id.car_name}, {driver_id.number_car}\n"
                   # f"<b>Статус: </b>{status_text}\n"
                   f"<b>Телефон: </b>{driver_id.phone}\n"
                   f"<b>Баланс: </b> {driver_id.price}рублей\n\n"
                   # f"<b>Бонусы</b> {driver_id.price}\n\n"
                   # f"<b>Стоимость выхода на линию:</b> {driver_id.price}\n"
                   f"Ночной тариф с <b>23:01</b> до <b>06:01</b>")
    await bot.send_photo(chat_id=message.from_user.id,
                         photo=driver_id.photo_car,
                         caption=text_driver)
