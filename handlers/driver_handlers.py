import os
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode
from dotenv import load_dotenv
from datetime import datetime, timedelta

from app.database.requests import get_all_orders, get_driver, delete_order_execution, delete_order_pass, \
    get_order_driver, save_free_ride, set_chat_id_driver, set_chat_id_user, update_driver, get_settings
from app.driver_activity_check import mark_driver_responded
from app.dialog.states import StartOrder
from filters.chat_type import ChatTypeFilter
from app.change_price import Settings
from middleware.driver_active_middleware import DriverActiveMiddleware
import app.keyboards as kb
import app.kb.kb_shop as kb_sh

driver_router = Router()
driver_router.message.filter(ChatTypeFilter(['private']))
driver_router.callback_query.middleware(DriverActiveMiddleware())
driver_router.message.middleware(DriverActiveMiddleware())
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
        
        # Проверяем автораспределение
        from app.database.requests import get_settings, get_next_available_driver, check_and_reset_if_needed, increment_driver_order_count, mark_driver_inactive
        from aiogram.exceptions import TelegramBadRequest
        settings = await get_settings()
        auto_distribution = settings.auto_distribution if settings else False
        
        if auto_distribution:
            # Автораспределение включено - отправляем следующему водителю
            await check_and_reset_if_needed()
            next_driver = await get_next_available_driver(exclude_driver_id=driver_id.tg_id)
            
            if not next_driver:
                next_driver = await get_next_available_driver()
            
            # Сбрасываем счетчик текущего водителя
            from app.database.requests import async_session
            from app.database.models import Driver
            from sqlalchemy import update
            async with async_session() as session:
                await session.execute(
                    update(Driver)
                    .where(Driver.tg_id == driver_id.tg_id)
                    .values(order_count=False)
                )
                await session.commit()
            
            if not next_driver:
                # Если нет доступных водителей, отправляем в группу
                message_driver = await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                        text=text_order,
                                                        reply_markup=await kb.accept(order_id.id))
            else:
                # Проверяем баланс водителя
                if next_driver.price <= 0:
                    await mark_driver_inactive(next_driver.tg_id)
                    # Отправляем в группу, если водитель без баланса
                    message_driver = await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                            text=text_order,
                                                            reply_markup=await kb.accept(order_id.id))
                else:
                    try:
                        message_driver = await bot.send_message(
                            chat_id=next_driver.tg_id,
                            text=text_order,
                            reply_markup=await kb.accept_or_skip(order_id.id)
                        )
                        await increment_driver_order_count(next_driver.tg_id)
                        await set_chat_id_user(order_id.id, driver_id=str(next_driver.tg_id), chat_id_driver=str(message_driver.message_id))
                        
                        # Отправляем заказ админам для мониторинга
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
                                        reply_markup=await kb.accept(order_id.id)
                                    )
                                    admin_messages_dict[str(admin_id)] = admin_message.message_id
                                except TelegramBadRequest as e:
                                    pass
                        except Exception as e:
                            pass
                        
                        # Сохраняем message_id админов в базу
                        if admin_messages_dict:
                            await set_chat_id_user(order_id.id, admin_messages=admin_messages_dict)
                    except TelegramBadRequest as e:
                        if "chat not found" in str(e).lower():
                            await mark_driver_inactive(next_driver.tg_id)
                            # Отправляем в группу, если водитель недоступен
                            message_driver = await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                                    text=text_order,
                                                                    reply_markup=await kb.accept(order_id.id))
                        else:
                            raise e
        else:
            # Автораспределение выключено - отправляем в группу
            message_driver = await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                                    text=text_order,
                                                    reply_markup=await kb.accept(order_id.id))

        await callback.message.edit_text(f'Вы отказались от заказа <b>№{order_id.id}</b>')
        await update_driver(driver_id.tg_id, price=int(driver_id.price + int(order_id.price * 0.10)))
        
        # Отправляем уведомление админам об отмене заказа водителем (только если автораспределение включено)
        if auto_distribution:
            try:
                admin_list = bot.my_admins_list if hasattr(bot, 'my_admins_list') else []
                for admin_id in admin_list:
                    try:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=f"❌ <b>Водитель отменил заказ</b>\n\n"
                                 f"Номер заказа: <b>{order_id.id}</b>\n"
                                 f"Водитель: <b>{driver_id.name}</b>\n"
                                 f"Пассажир: <b>{order_id.user_rel.phone}</b>"
                        )
                    except TelegramBadRequest as e:
                        pass
            except Exception as e:
                pass

        await set_chat_id_driver(order_id.id, message_id_pass.message_id)
        await set_chat_id_user(order_id.id, chat_id_driver=str(message_driver.message_id))

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
        await set_chat_id_user(order_id.id, chat_id_driver=str(message_driver.message_id))

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
        await set_chat_id_user(order_id.id, chat_id_driver=str(message_driver.message_id))

        await bot.edit_message_reply_markup(
            chat_id=order_id.user_rel.tg_id,
            message_id=message_pass.message_id,
            reply_markup=await kb.delete_order(order_id.id))
    except AttributeError:
        await callback.answer('')
        await callback.message.answer('Пассажир отменил заказ')


@driver_router.callback_query(F.data.startswith('finish_'))
async def finish(callback: CallbackQuery, bot: Bot, dialog_manager: DialogManager):
    try:
        await callback.answer('')
        order_id = await get_all_orders(callback.data.split('_')[1])
        driver_id = await get_driver(callback.from_user.id)
        status = await get_settings()
        bg_manager = dialog_manager.bg(user_id=order_id.user_rel.tg_id)
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
        # Удаляем запись о начале выполнения заказа
        # await delete_order_execution(order_id.id, driver_id.id)
        # Увеличиваем счетчик поездок
        # Бесплатные поездки
        user_free_ride = order_id.user_rel.free_ride
        active_paid_free = order_id.user_rel.paid_free
        paid_free_value = order_id.user_rel.paid_free_value

        if status.free_ride:

            user_free_ride += 1
            if user_free_ride >= status.free_price or paid_free_value == '1':
                # Обнуляем счетчик после 10-й поездки
                free_ride_count = 0
                # ставим в таблице ноль и активурем paid_free = true
                await save_free_ride(order_id.user_rel.tg_id,
                                     free_ride_count,
                                     paid_free_bool=True)  # ставим в таблице ноль и активурем paid_free = true

                try:
                    # удаляю сообщение у пользователя
                    await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id_pass)
                except TelegramBadRequest as e:
                    if "message to delete not found" in str(e):
                        # Логирование или обработка конкретного случая, если сообщение не найдено
                        print("Сообщение уже удалено или не найдено.")
                    else:
                        raise e
                
                # Отправляем поздравление
                await bot.send_message(
                    chat_id=order_id.user_rel.tg_id,
                    text=f'🎉 <b>Поздравляем! Ваша следующая поездка будет бесплатной!</b> 🎉\n\n'
                         f'Выберите тип поездки:'
                )
                
                # Запускаем диалог для выбора платно/бесплатно
                await bg_manager.start(
                    state=StartOrder.user,
                    mode=StartMode.RESET_STACK,
                )
            else:
                free_ride = user_free_ride
                await save_free_ride(order_id.user_rel.tg_id, free_ride, paid_free_bool=False)
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
                                            f'Спасибо что пользуетесь нашими услугами 🙏\n\n'
                                            f'До бесплатной поездки осталось {status.free_price - free_ride}',
                                       reply_markup=await kb.main())
                # text_driver = (f"Заказ выполнен✅.\n"
                #                f"Спасибо что пользуетесь нашими услугами 🙏\n\n"
                #                f"До бесплатной поездки осталось {status.free_price - free_ride}")
                # await bg_manager.start(
                #     state=StartOrder.user,  # важно!
                #     data={"text": text_driver},
                #     # это будет в Format('{text}')
                #     mode=StartMode.RESET_STACK,
                # )

        # Бесплатные поездки выключены
        else:
            if user_free_ride == 0 or paid_free_value == '2':
                free_ride = 1
                await save_free_ride(order_id.user_rel.tg_id, free_ride, paid_free_bool=False)
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
            # text_driver = (f'Заказ выполнен✅.\n'
            #                f'Спасибо что пользуетесь нашими услугами 🙏\n\n')
            # await bg_manager.start(
            #     state=StartOrder.user,  # важно!
            #     data={"text": text_driver},
            #     # это будет в Format('{text}')
            #     mode=StartMode.RESET_STACK
            # )


        await callback.message.delete()
    except AttributeError:
        await callback.answer('')
        await callback.message.answer('Пассажир отменил заказ')


# тестирую личную карточку водителя
@driver_router.message(Command('driver'))
async def driver_lk(message: Message, bot: Bot):
    driver_id = await get_driver(message.from_user.id)
    settings = await get_settings()
    auto_distribution = settings.auto_distribution if settings else False
    
    text_driver = f"Здравствуйте, {driver_id.name}\n\n"
    text_driver += f"<b>Автомобиль: </b>{driver_id.car_name}, {driver_id.number_car}\n"
    
    # Показываем статус только если автораспределение включено
    if auto_distribution:
        if driver_id.active:
            status_text = "🟢 На линии"
        else:
            status_text = "🔴 Не на линии"
        text_driver += f"<b>Статус: </b>{status_text}\n"
    
    text_driver += f"<b>Телефон: </b>{driver_id.phone}\n"
    text_driver += f"<b>Баланс: </b> {driver_id.price}рублей"
    
    await bot.send_photo(chat_id=message.from_user.id,
                         photo=driver_id.photo_car,
                         caption=text_driver)


# ------------------Обработка ответа водителя на проверку активности---------------
@driver_router.callback_query(F.data == 'driver_activity_yes')
async def driver_activity_yes(callback: CallbackQuery, bot: Bot):
    """Водитель подтвердил активность"""
    await callback.answer('')
    driver = await get_driver(callback.from_user.id)
    if not driver:
        await callback.message.edit_text('Ошибка: вы не найдены в системе водителей')
        return
    
    # Отмечаем, что водитель ответил (обновляет время последнего взаимодействия)
    mark_driver_responded(callback.from_user.id)
    
    # Устанавливаем активность
    await update_driver(callback.from_user.id, active=True)
    
    await callback.message.edit_text('✅ <b>Вы подтвердили активность</b>\n\nВы остаетесь на линии.')


@driver_router.callback_query(F.data == 'driver_activity_no')
async def driver_activity_no(callback: CallbackQuery, bot: Bot):
    """Водитель подтвердил неактивность"""
    await callback.answer('')
    driver = await get_driver(callback.from_user.id)
    if not driver:
        await callback.message.edit_text('Ошибка: вы не найдены в системе водителей')
        return
    
    # Отмечаем, что водитель ответил
    mark_driver_responded(callback.from_user.id)
    
    # Устанавливаем неактивность
    await update_driver(callback.from_user.id, active=False)
    
    await callback.message.edit_text('🔴 <b>Вы переведены в неактивный статус</b>\n\nДля возврата на линию нажмите /start и выберите "Активен"')
