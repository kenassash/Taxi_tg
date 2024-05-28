import os
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from dotenv import load_dotenv

from app.database.requests import get_all_orders, get_driver, delete_order_execution, delete_order_pass, \
    get_order_driver
from filters.chat_type import ChatTypeFilter
import app.keyboards as kb

driver_router = Router()
driver_router.message.filter(ChatTypeFilter(['private']))
load_dotenv()


@driver_router.callback_query(F.data.startswith('close_'))
async def close(callback: CallbackQuery, bot: Bot):
    try:
        await callback.answer('')
        order_id = await get_all_orders(callback.data.split('_')[1])
        driver_id = await get_driver(callback.from_user.id)
        message_id = callback.data.split('_')[2]

        # Удаляем запись запись о начале выполнения заказа
        await delete_order_execution(order_id.id, driver_id.id)

        await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id)
        message_id_pass = await bot.send_message(chat_id=order_id.user_rel.tg_id,
                                                 text=f'Ожидайте ⌛\n'
                                                      f'Будет назначен новый водитель в ближайшее время\n',
                                                 reply_markup=await kb.delete_order(order_id.id))
        await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                               text=f'Водитель {driver_id.name} отменил выпонлнение заказа\n'
                                    f"Телефон <b>+{order_id.user_rel.phone}</b>\n\n"
                                    f"Начальная точка: <b>{order_id.point_start}</b>\n\n"
                                    f"Конечная точка: <b>{order_id.point_end}</b>\n\n"
                               # f"Расстояние: <b>{order_id.distance}км</b>\n\n"
                               # f"Время пути: <b>{order_id.time_way}мин</b>\n\n"
                                    f"Цена: <b>{order_id.price}Р</b>\n\n",
                               reply_markup=await kb.accept(order_id.id, message_id_pass.message_id))

        await callback.message.edit_text(f'Вы отказались от заказа <b>№{order_id.id}</b>')


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
        message_id = callback.data.split('_')[3]

        await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id)


        message_pass = await bot.send_photo(chat_id=order_id.user_rel.tg_id,
                                            photo=driver.photo_car,
                                            caption=f'Номер телефона:<b> +{driver.phone}</b>\n\n'
                                                    f'Автомобиль:<b> {driver.car_name}</b>\n\n'
                                                    f'Номер: <b>{driver.number_car}</b>\n\n'
                                                    f'Цена поездки: <b>{order_id.price}Р</b>\n\n'
                                                    f'Будет у вас через <b>{time_wait} мин.</b>',
                                            reply_markup=await kb.delete_order(order_id.id))


        await callback.message.edit_text(f"Заказ <b>{order_id.id}</b>\n\n"
                                         f"Телефон <b>+{order_id.user_rel.phone}</b>\n\n"
                                         f"Начальная точка: <b>{order_id.point_start}</b>\n\n"
                                         f"Конечная точка: <b>{order_id.point_end}</b>\n\n"
                                         # f"Расстояние: <b>{order_id.distance}км</b>\n\n"
                                         # f"Время пути: <b>{order_id.time_way}мин</b>\n\n"
                                         f"Цена: <b>{order_id.price}Р</b>\n\n",
                                         reply_markup=await kb.on_the_spot_kb(order_id.id, message_pass.message_id))
        # reply_markup = await kb.close_and_finish(order_id.id)
    except AttributeError:
        await callback.answer('')
        await callback.message.answer('Пассажир отменил заказ')


@driver_router.callback_query(F.data.startswith('onthespot_'))
async def on_the_spot(callback: CallbackQuery, bot: Bot):
    try:
        await callback.answer('')
        order_id = await get_all_orders(callback.data.split('_')[1])
        driver = await get_driver(callback.from_user.id)
        message_id = callback.data.split('_')[2]

        await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id)

        message_pass = await bot.send_photo(chat_id=order_id.user_rel.tg_id,
                                            photo=driver.photo_car,
                                            caption=f'<b>Водитель приехал за вами ✅🚕</b>\n\n'
                                                    f'Номер телефона:<b> +{driver.phone}</b>\n\n'
                                                    f'Автомобиль:<b> {driver.car_name}</b>\n\n'
                                                    f'Номер: <b>{driver.number_car}</b>\n\n'
                                                    f'Цена поездки: <b>{order_id.price}Р</b>\n\n',
                                            reply_markup=await kb.delete_order(order_id.id))
        await callback.message.edit_text(f"Заказ <b>{order_id.id}</b>\n\n"
                                         f"Телефон <b>+{order_id.user_rel.phone}</b>\n\n"
                                         f"Начальная точка: <b>{order_id.point_start}</b>\n\n"
                                         f"Конечная точка: <b>{order_id.point_end}</b>\n\n"
                                         # f"Расстояние: <b>{order_id.distance}км</b>\n\n"
                                         # f"Время пути: <b>{order_id.time_way}мин</b>\n\n"
                                         f"Цена: <b>{order_id.price}Р</b>\n\n",
                                         reply_markup=await kb.close_and_finish(order_id.id, message_pass.message_id))
    except AttributeError:
        await callback.answer('')
        await callback.message.answer('Пассажир отменил заказ')


@driver_router.callback_query(F.data.startswith('finish_'))
async def finish(callback: CallbackQuery, bot: Bot):
    try:
        await callback.answer('')
        order_id = await get_all_orders(callback.data.split('_')[1])
        driver_id = await get_driver(callback.from_user.id)
        message_id_pass = callback.data.split('_')[2]
        # Удаляем запись запись о начале выполнения заказа
        # await delete_order_execution(order_id.id, driver_id.id)


        await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id_pass)
        await bot.send_message(chat_id=order_id.user_rel.tg_id,
                               text=f'Заказ выполнен✅.\n'
                                    f'Спасибо что пользуетесь нашими услугами 🙏\n',
                               reply_markup=await kb.main())
        await callback.message.delete()
    except AttributeError:
        await callback.answer('')
        await callback.message.answer('Пассажир отменил заказ')


@driver_router.callback_query(F.data.startswith('deleteorder_'))
async def delete_order_passager(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer('')
    await callback.message.answer('Заказ отменен')
    order_id = callback.data.split('_')[1]
    driver_id = await get_order_driver(order_id)

    # Проверка, если список drivers_reply пуст
    if not driver_id.drivers_reply:
        await callback.message.answer('Нет водителей для данного заказа')
    else:
        driver = driver_id.drivers_reply[0]
        await bot.send_message(chat_id=driver.tg_id, text='Пассажир отменил заказ')

    await delete_order_pass(order_id)
    await state.clear()
