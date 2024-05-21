import os
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from dotenv import load_dotenv

from app.change_price import Settings
from filters.chat_type import ChatTypeFilter
from aiogram import Bot
import app.keyboards as kb
from app.database.requests import get_all_orders, get_driver, start_order_execution, delete_order_execution

user_group_router = Router()
user_group_router.message.filter(ChatTypeFilter(['group', 'supergroup']))
load_dotenv()


# restricted_words = {'кабан', 'хомяк', 'выпухоль'}


# def clean_text(text: str):
#     return text.translate(str.maketrans('', '', punctuation))

# @user_group_router.message()
# async def cleaner(message: Message):
#     if restricted_words.intersection(message.text.lower().split()):
#         await message.answer(f'{message.from_user.first_name}, соблюдайте порядок чата')
#         await message.delete()

# @user_group_router.message(CommandStart())
# async def cmd_start(message: Message):
#     await message.answer(f'{message.chat.id}')


@user_group_router.callback_query(F.data.startswith('accept_'))
async def accept(callback: CallbackQuery, bot: Bot, state: FSMContext):
    try:
        await callback.answer('')
        order_id = await get_all_orders(callback.data.split('_')[1])
        message_id_pass = callback.data.split('_')[2]
        driver = await get_driver(callback.from_user.id)
        # сообщение id предыдущее (ожидание чтоб удалить)

        # Создаем запись о начале выполнения заказа
        await start_order_execution(order_id.id, driver.id)
        # удаляю сообщение у пользователя
        await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id_pass)

        # await bot.send_photo(chat_id=order_id.user_rel.tg_id, photo=driver.photo_car, caption=f'За вами приедет такси <b>{driver.car_name} {driver.number_car}</b>\n')
        # await bot.send_message(chat_id=callback.from_user.id,
        #                        text=callback.message.text,
        #                        reply_markup=await kb.close_and_finish(order_id.id))
        # await bot.send_message(chat_id=callback.from_user.id,
        #                        text=callback.message.text)
        message_pass = await bot.send_photo(chat_id=order_id.user_rel.tg_id,
                                            photo=driver.photo_car,
                                            caption=f'Водитель принял ваше предложение 🤝\n\n'
                                                    f'Номер телефона:<b> +{driver.phone}</b>\n\n'
                                                    f'Автомобиль:<b> {driver.car_name}</b>\n\n'
                                                    f'Номер: <b>{driver.number_car}</b>\n\n'
                                                    f'Цена поездки: <b>{order_id.price}Р</b>\n\n'
                                                    f'Водитель подъедет в скором времени',
                                            reply_markup=await kb.delete_order(order_id.id))
        # message_pass = await bot.edit_message_media(chat_id=order_id.user_rel.tg_id,
        #                                             message_id=message_id_pass,
        #                                             media=InputMediaPhoto
        #                                             (
        #                                                 media=driver.photo_car,
        #                                                 caption=f'Водитель принял ваше предложение 🤝\n\n'
        #                                             f'Номер телефона:<b> +{driver.phone}</b>\n\n'
        #                                             f'Автомобиль:<b> {driver.car_name}</b>\n\n'
        #                                             f'Номер: <b>{driver.number_car}</b>\n\n'
        #                                             f'Цена поездки: <b>{order_id.price}Р</b>\n\n'
        #                                             f'Водитель подъедет в скором времени',),
        #                                             reply_markup=await kb.delete_order(order_id.id))

        # Обновляем состояние, сохраняя идентификатор отправленного сообщения

        message_driver = await bot.send_message(chat_id=callback.from_user.id,
                                                     text=f"Заказ <b>{order_id.id}</b>\n\n"
                                                          f"Телефон <b>+{order_id.user_rel.phone}</b>\n\n"
                                                          f"Начальная точка: <b>{order_id.point_start}</b>\n\n"
                                                          f"Конечная точка: <b>{order_id.point_end}</b>\n\n"
                                                     # f"Расстояние: <b>{order_id.distance}км</b>\n\n"
                                                     # f"Время пути: <b>{order_id.time_way}мин</b>\n\n"
                                                          f"Цена: <b>{order_id.price}Р</b>\n\n"
                                                          f'⌚ Выберите время подачи: ⬇️',
                                                     reply_markup=await kb.time_wait(order_id.id,
                                                                                     message_pass.message_id))


        await callback.message.edit_text(text=f'Такси бот', reply_markup=await kb.go_to_order())

    except AttributeError:
        await callback.answer('')
        await callback.message.edit_text('Пассажир отменил заказ')

#
# @user_group_router.callback_query(F.data.startswith('close_'))
# async def close(callback: CallbackQuery, bot: Bot):
#     try:
#         await callback.answer('')
#         order_id = await get_all_orders(callback.data.split('_')[1])
#         driver_id = await get_driver(callback.from_user.id)
#
#         # Удаляем запись запись о начале выполнения заказа
#         await delete_order_execution(order_id.id, driver_id.id)
#
#         await callback.message.edit_text(f'Вы отказались от заказа <b>№{order_id.id}</b>')
#         await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
#                                text=f'Водитель {callback.from_user.first_name} отменил выпонление заказа\n'
#                                     f"Телефон <b>+{order_id.user_rel.phone}</b>\n\n"
#                                     f"Начальная точка: <b>{order_id.point_start}</b>\n\n"
#                                     f"Конечная точка: <b>{order_id.point_end}</b>\n\n"
#                                # f"Расстояние: <b>{order_id.distance}км</b>\n\n"
#                                # f"Время пути: <b>{order_id.time_way}мин</b>\n\n"
#                                     f"Цена: <b>{order_id.price}Р</b>\n\n",
#                                reply_markup=await kb.accept(order_id.id, callback.message.message_id))
#
#         await bot.send_message(chat_id=order_id.user_rel.tg_id,
#                                text=f'Ожидайте ⌛\n'
#                                     f'Будет назначен новый водитель в ближайшее время\n',
#                                reply_markup=await kb.delete_order(order_id.id))
#     except AttributeError:
#         await callback.answer('')
#         await callback.message.edit_text('Пассажир отменил заказ')
#
#
# @user_group_router.callback_query(F.data.startswith('timewait_'))
# async def timewait(callback: CallbackQuery, bot: Bot):
#     try:
#         await callback.answer('')
#         order_id = await get_all_orders(callback.data.split('_')[1])
#
#         driver = await get_driver(callback.from_user.id)
#         time_wait = callback.data.split('_')[2]
#
#         # await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id_id)
#
#         await bot.send_message(chat_id=order_id.user_rel.tg_id,
#                                text=f'Водитель принял ваше предложение 🤝\n\n'
#                                     f'Будет у вас через <b>{time_wait} мин.</b>',
#                                reply_markup=await kb.delete_order(order_id.id))
#
#         # await bot.send_photo(chat_id=order_id.user_rel.tg_id,
#         #                      photo=driver.photo_car,
#         #                      caption=f'Водитель принял ваше предложение 🤝\n\n'
#         #                              f'Номер телефона:<b> +{driver.phone}</b>\n\n'
#         #                              f'Автомобиль:<b> {driver.car_name}</b>\n\n'
#         #                              f'Номер: <b>{driver.number_car}</b>\n\n'
#         #                              f'Цена поездки: <b>{order_id.price}Р</b>\n\n'
#         #                              f'Будет у вас через {time_wait} мин.')
#         # await bot.send_message(chat_id=callback.from_user.id,
#         #                        text='принять или завершить',
#         #                        reply_markup=await kb.close_and_finish(order_id.id))
#         await callback.message.edit_text(f"Заказ <b>{order_id.id}</b>\n\n"
#                                          f"Телефон <b>+{order_id.user_rel.phone}</b>\n\n"
#                                          f"Начальная точка: <b>{order_id.point_start}</b>\n\n"
#                                          f"Конечная точка: <b>{order_id.point_end}</b>\n\n"
#                                          # f"Расстояние: <b>{order_id.distance}км</b>\n\n"
#                                          # f"Время пути: <b>{order_id.time_way}мин</b>\n\n"
#                                          f"Цена: <b>{order_id.price}Р</b>\n\n",
#                                          reply_markup=await kb.on_the_spot_kb(order_id.id))
#         # reply_markup = await kb.close_and_finish(order_id.id)
#     except AttributeError:
#         await callback.answer('')
#         await callback.message.answer('Пассажир отменил заказ')
#
#
# @user_group_router.callback_query(F.data.startswith('onthespot_'))
# async def on_the_spot(callback: CallbackQuery, bot: Bot):
#     try:
#         await callback.answer('')
#         order_id = await get_all_orders(callback.data.split('_')[1])
#         driver = await get_driver(callback.from_user.id)
#
#         # await bot.mes(chat_id=order_id.user_rel.tg_id)
#         await bot.send_message(chat_id=order_id.user_rel.tg_id,
#                                text=f'<b>Водитель приехал за вами ✅🚕</b>\n\n',
#                                reply_markup=await kb.delete_order(order_id.id)
#                                # f'Номер телефона:<b> +{driver.phone}</b>\n\n'
#                                # f'Автомобиль:<b> {driver.car_name}</b>\n\n'
#                                # f'Номер: <b>{driver.number_car}</b>\n\n'
#                                # f'Цена поездки: <b>{order_id.price}Р</b>\n\n',
#                                )
#         await callback.message.edit_text(f"Заказ <b>{order_id.id}</b>\n\n"
#                                          f"Телефон <b>+{order_id.user_rel.phone}</b>\n\n"
#                                          f"Начальная точка: <b>{order_id.point_start}</b>\n\n"
#                                          f"Конечная точка: <b>{order_id.point_end}</b>\n\n"
#                                          # f"Расстояние: <b>{order_id.distance}км</b>\n\n"
#                                          # f"Время пути: <b>{order_id.time_way}мин</b>\n\n"
#                                          f"Цена: <b>{order_id.price}Р</b>\n\n",
#                                          reply_markup=await kb.close_and_finish(order_id.id))
#     except AttributeError:
#         await callback.answer('')
#         await callback.message.answer('Пассажир отменил заказ')
#
#
# @user_group_router.callback_query(F.data.startswith('finish_'))
# async def finish(callback: CallbackQuery, bot: Bot, state: FSMContext):
#     try:
#         await callback.answer('')
#         order_id = await get_all_orders(callback.data.split('_')[1])
#         driver_id = await get_driver(callback.from_user.id)
#         # Удаляем запись запись о начале выполнения заказа
#         # await delete_order_execution(order_id.id, driver_id.id)
#
#         # Извлечение данных из состояния
#         data = await state.get_data()
#         print(str(data))
#         sent_message_pass = data.get('sent_message_pass')
#         sent_message_driver = data.get('sent_message_driver')
#         print(sent_message_pass, sent_message_driver)
#
#         # Удаляем сообщение, если идентификатор существует
#         # if sent_message_id:
#         #     await bot.delete_message(chat_id=callback.message.chat.id, message_id=sent_message_id)
#         #     # Очищаем состояние
#         #     await state.update_data(sent_message_id=None)
#
#         await callback.message.delete()
#
#         # await callback.message.edit_text(f'Заказ выполнен {order_id.id}')
#         # await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
#         #                        text=f"Заказ № {order_id.id} выполнен ✅\n\n"
#         #                             f"Водителем {callback.from_user.first_name}")
#         await bot.send_message(chat_id=order_id.user_rel.tg_id,
#                                text=f'Заказ выполнен✅.\n'
#                                     f'Спасибо что пользуетесь нашими услугами 🙏\n',
#                                reply_markup=await kb.main())
#     except AttributeError:
#         await callback.answer('')
#         await callback.message.answer('Пассажир отменил заказ')
