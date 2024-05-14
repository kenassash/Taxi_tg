import hashlib
import json
import os
import re

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, or_f, Command
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup, StateFilter
from aiogram import Bot
from dotenv import load_dotenv

import app.keyboards as kb
from app.change_price import Settings
from app.geolocation import coords_to_address, addess_to_coords
from app.database.requests import set_user, set_order, get_all_orders, get_driver, active_driver, get_user, add_car
from filters.chat_type import ChatTypeFilter
from app.calculate import length_way

router = Router()
router.message.filter(ChatTypeFilter(['private']))
load_dotenv()


# ----------------Отменить заказ---------------
@router.message(F.text == 'Отменить')
async def cancel_order_reply(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(f'Вы отменили заказ. Нажмитке /start чтоб начать поездку', reply_markup=ReplyKeyboardRemove())


# ----------------Шаг назад---------------
@router.callback_query(StateFilter('*'), F.data == 'backbutton_')
async def backbutton(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    previous = None
    for step in AddOrder.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await callback.answer('')
            await callback.message.edit_text(f'Вы вернулись к прошлому шагу\n{AddOrder.texts[previous.state]}\n')
            return
        previous = step


# ----------------Отменить заказ---------------
@router.callback_query(F.data.startswith('cancelorder_'))
async def cancelorder(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(f'Вы отменили')


class AddOrder(StatesGroup):
    point_start = State()
    point_end = State()
    finish = State()

    # coordinat_start_x = State()
    # coordinat_start_y = State()
    # coordinat_end_x = State()
    # coordinat_end_y = State()

    texts = {
        'AddOrder:point_start': 'Введите начальную точку заново',
        'AddOrder:point_end': 'Введите конечную точку заново',
    }


class AddUser(StatesGroup):
    phone = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    # Проверка, является ли пользователь таксистом
    drivers = await get_driver(message.from_user.id)
    if drivers and drivers.tg_id == message.from_user.id:
        await message.answer(f'<b>Добро пожаловать, Таксист {message.from_user.full_name}</b>😊\n\n',
                             reply_markup=await kb.driver_start_or_finish())
        # reply_markup = await kb.driver_start_or_finish()
        return

    tg_id = message.from_user.id
    user = await get_user(tg_id)

    if user:
        # Если пользователь уже есть в базе данных, приветствуем его
        await message.answer(f'<b>Добро пожаловать, {message.from_user.full_name}!</b> 😊',
                             reply_markup=await kb.main())
    else:
        # Если пользователь не найден в базе данных, запрашиваем номер телефона
        await message.answer(f'Добро пожаловать в такси городок!\n'
                             f'Пожалуйста, отправьте свой номер телефона для регистрации c помощью кнопки:',
                             reply_markup=await kb.phone())
        await state.set_state(AddUser.phone)


# Обработка полученного номера телефона
@router.message(AddUser.phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    # Обработка полученного номера телефона
    phone_number = message.contact.phone_number
    tg_id = message.from_user.id

    # Запись пользователя в базу данных
    await set_user(tg_id, phone_number)

    # Приветствие пользователя после успешной записи
    await message.answer(f'Вы зарегестрировались', reply_markup=ReplyKeyboardRemove())
    await message.answer(f'<b>Добро пожаловать, {message.from_user.full_name}!</b> 😊',
                         reply_markup=await kb.main())
    await state.clear()


@router.message(AddUser.phone)
async def process_invalid_phone(message: Message):
    # Обработка случая, когда пользователь отправляет что-то, кроме номера телефона
    await message.answer('Пожалуйста, используйте кнопку для отправки телефона')


@router.callback_query(F.data == 'neworder')
async def neworder(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer('')
    await callback.message.edit_text(
        f'<b>🅰️: Напишите  Улицу и № дома\n'
        f'Например: Южная 8</b>',
        reply_markup=await kb.cancel_order())
    await state.set_state(AddOrder.point_start)


@router.message(AddOrder.point_start, F.text)
async def point_starter(message: Message, state: FSMContext):
    await state.update_data(point_start=message.text)
    data = await state.get_data()
    await message.answer(f'<b>🅰️: {data["point_start"]}\n\n'
                         f'🅱️: Напишите куда поедите?\nНапример: Ленина 60;</b>',
                         reply_markup=await kb.back_button())
    await state.set_state(AddOrder.point_end)

    # try:
    #     if message.text:
    #         address_go = message.text
    #         longitude_end, latitude_end, trimmed_string = await addess_to_coords(address_go)
    #         print(trimmed_string)
    #         print(float(longitude_end), float(latitude_end))
    #     elif message.location:
    #         latitude_end = message.location.latitude
    #         longitude_end = message.location.longitude
    #         trimmed_string = await coords_to_address(longitude_end, latitude_end)
    #         print(float(longitude_end), float(latitude_end))
    #         print(trimmed_string)

    # except IndexError:
    #     await message.answer('Улица и дом не корретно введены')
    #     await state.clear()
    #     full_name = message.from_user.full_name
    #     await message.answer(f'<b>Добро пожаловать {full_name} </b>😊', reply_markup=await kb.main())
    #     return
    #
    # await state.update_data(point_start=trimmed_string,
    #                         coordinat_start_x=float(longitude_end),
    #                         coordinat_start_y=float(latitude_end))
    # data = await state.get_data()
    # point = data.get('point_start')
    # await message.answer(f'<b>🅰️: {point}\n\n'
    #                      f'🅱️: Напишите куда поедите?\nНапример: Ленина 60;</b>',
    #                      reply_markup=await kb.back_button())
    # await state.set_state(AddOrder.point_end)


@router.message(AddOrder.point_start)
async def point_start(message: Message, state: FSMContext):
    await message.answer(f'Введите корреткно от куда едите')


@router.message(AddOrder.point_end, F.text)
async def point_end(message: Message, state: FSMContext):
    await state.update_data(point_end=message.text, price=(100 + Settings.fix_price))
    data = await state.get_data()
    await message.answer(f"<b>🅰️: Начальная точка:</b> {data['point_start']}\n\n"
                         f"<b>🅱️: Конечная точка:</b> {data['point_end']}\n\n"
                         f"<b>Цена:</b> {data['price']}₽",
                         reply_markup=await kb.order_now())

    # try:
    #     if message.text:
    #         address_go = message.text
    #         longitude_end, latitude_end, trimmed_string = await addess_to_coords(address_go)
    #         print(trimmed_string)
    #         print(float(longitude_end), float(latitude_end))
    #     elif message.location:
    #         latitude_end = message.location.latitude
    #         longitude_end = message.location.longitude
    #         trimmed_string = await coords_to_address(longitude_end, latitude_end)
    #         print(float(longitude_end), float(latitude_end))
    #         print(trimmed_string)
    # except IndexError:
    #     await message.answer('Улица и дом не корретно')
    #     await state.clear()
    #     full_name = message.from_user.full_name
    #     await message.answer(f'<b>Добро пожаловать {full_name} </b>😊', reply_markup=await kb.main())
    #     return
    # await state.update_data(point_end=trimmed_string,
    #                         coordinat_end_x=float(longitude_end),
    #                         coordinat_end_y=float(latitude_end))

    # point = data.get('point_start')
    # end = data.get('point_end')
    # await message.answer(f'<b>🅰️: {point}\n\n'
    #                      f'🅱️: {end}\n\n</b>',
    #                      reply_markup=await kb.back_button())
    # data = await state.get_data()
    # distance, time_way, price = await length_way(data['coordinat_start_x'],
    #                                              data['coordinat_start_y'],
    #                                              data['coordinat_end_x'],
    #                                              data['coordinat_end_y'])
    # await state.update_data(distance=distance, time_way=time_way, price=price)
    # await message.answer(f"<b>🅰️: Начальная точка:</b> {data['point_start']}\n\n"
    #                      f"<b>🅱️: Конечная точка:</b> {data['point_end']}\n\n"
    #                      f"<b>Расстояние:</b> {distance}км\n\n"
    #                      f"<b>Время пути:</b> {time_way}мин\n\n"
    #                      f"<b>Цена:</b> {price}₽",
    #                      reply_markup=await kb.order_now())
    await state.set_state(AddOrder.finish)


@router.message(AddOrder.point_end)
async def point_end(message: Message, state: FSMContext):
    await message.answer('Введите корреткно куда едите')


@router.callback_query(AddOrder.finish, F.data == 'order_now')
async def finish_price(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer('')
    data = await state.get_data()
    user_id = await get_user(callback.from_user.id)
    order_id = await set_order(user_id.id, data)
    order_data = await get_all_orders(order_id)
    await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                           text=f"Заказ <b>{order_id}</b>\n\n"
                                f"Телефон <b>+{user_id.phone}</b>\n\n"
                                f"Начальная точка: <b>{order_data.point_start}</b>\n\n"
                                f"Конечная точка: <b>{order_data.point_end}</b>\n\n"
                           # f"<b>Расстояние:</b> {order_data.distance}км\n\n"
                           # f"<b>Время пути:</b> {order_data.time_way}мин\n\n"
                                f"Цена: <b>{order_data.price}Р</b>",
                           reply_markup=await kb.accept(order_id, callback.message.message_id))
    await callback.message.edit_text(f"<b>Ожидайте водителя⌛</b>\n\n"
                                     f"Начальная точка: <b>{order_data.point_start}</b>\n\n"
                                     f"Конечная точка: <b>{order_data.point_end}</b>\n\n"
                                     # f"<b>Расстояние:</b> {order_data.distance}км\n\n"
                                     # f"<b>Время пути:</b> {order_data.time_way}мин\n\n"
                                     f"Цена: <b>{order_data.price}Р</b>")

    await state.clear()


@router.message(AddOrder.point_end)
async def point_end(message: Message, state: FSMContext):
    await message.answer('Введите корреткно куда едите')


#-------------отправка сообщения администраторам\менеджерам
class SendMessage(StatesGroup):
    send_manager = State()
@router.message(Command('manager'))
async def send_manager_call(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SendMessage.send_manager)
    await message.answer(f'🖊️<b>Напишите сообщение менеджеру Такси городок</b> 🚕',
                                     reply_markup=await kb.cancel_order())

@router.message(SendMessage.send_manager)
async def get_manager(message: Message, state: FSMContext, bot: Bot):
    user = await get_user(message.from_user.id)
    if message.text:
        await state.update_data(send_manager=message.text)
        await bot.send_message(chat_id=os.getenv('CHAT_ID_ADMIN'),
                             text=f'Пользователь ник нейм: <b>{message.from_user.username}</b>\n'
                                  f'Имя: <b>{message.from_user.first_name}</b>\n'
                                  f'CHAT ID: <b>{message.from_user.id}</b>\n'
                                  f'Телефон: <b>+{user.phone}</b>\n'
                                  f'------------------------------\n'
                                  f'Сообщение:\n'
                                  f'<i>{message.text}</i>\n')
        await state.clear()
        await message.answer('Спасибо за сообщение. В скором времени с вами свяжется менеджер',
                             reply_markup=await kb.main())

    elif message.voice:
        await state.update_data(send_manager=message.voice)
        await bot.send_voice(chat_id=os.getenv('CHAT_ID_ADMIN'),
                             caption=f'Пользователь ник нейм: <b>{message.from_user.username}</b>\n'
                                  f'Имя: <b>{message.from_user.first_name}</b>\n'
                                  f'CHAT ID: <b>{message.from_user.id}</b>\n'
                                  f'Телефон: <b>+{user.phone}</b>\n',
                             voice=message.voice.file_id)
        await state.clear()
        await message.answer('Спасибо за голосовое сообщение. В скором времени с вами свяжется менеджер',
                             reply_markup=await kb.main())
    else:
        await message.answer('Отправь текстовое или голосовое сообщение')


# ----------------Команды для Таксистов---------------
# ----------------Выйти на линию ---------------------
@router.callback_query(F.data.startswith('driverstart_'))
async def driver_start(callback: CallbackQuery):
    await callback.answer('')
    await active_driver(callback.message.chat.id, is_start=True)
    await callback.message.edit_text('Вы вышли на линию')


# ----------------Уйти с линии на линию ---------------------
@router.callback_query(F.data.startswith('driverfinish_'))
async def driver_finish(callback: CallbackQuery):
    await callback.answer('')
    await active_driver(callback.message.chat.id, is_start=False)
    await callback.message.edit_text('Вы ушли с линии')


# подать заявку в такси

class AddDrivercar(StatesGroup):
    phone = State()
    car_name = State()
    number_car = State()
    photo_car = State()


@router.message(Command('add_car'))
async def add_phone1(message: Message, state: FSMContext):
    await state.set_state(AddDrivercar.phone)
    await message.answer('Отправь номер телефона', reply_markup=await kb.cancel_order())


@router.message(AddDrivercar.phone, F.text)
async def add_car_name(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(AddDrivercar.car_name)
    await message.answer('Введите название марки машины', reply_markup=await kb.cancel_order())


@router.message(AddDrivercar.phone)
async def add_phone2(message: Message, state: FSMContext):
    await message.answer('Отправь телефон через кнопку')


@router.message(AddDrivercar.car_name, F.text)
async def add_number_car(message: Message, state: FSMContext):
    await state.update_data(car_name=message.text)
    await state.set_state(AddDrivercar.number_car)
    await message.answer('Введите гос номер машины', reply_markup=await kb.cancel_order())


@router.message(AddDrivercar.car_name)
async def add_car_name(message: Message, state: FSMContext):
    await message.answer('Введите коррекно название машины')


@router.message(AddDrivercar.number_car, F.text)
async def add_tg_id(message: Message, state: FSMContext):
    await state.update_data(number_car=message.text)
    await state.set_state(AddDrivercar.photo_car)
    await message.answer('Отправь фото машины', reply_markup=await kb.cancel_order())


@router.message(AddDrivercar.number_car)
async def add_number_car(message: Message, state: FSMContext):
    await message.answer('Отправь коррекно гос номер')


@router.message(AddDrivercar.photo_car, F.photo)
async def add_item_category(message: Message, state: FSMContext, bot: Bot):
    message_user = message.from_user.id
    await state.update_data(photo_car=message.photo[-1].file_id, tg_id=message_user)
    data = await state.get_data()
    driver_id = await add_car(data)

    # await message.answer_photo(photo=data['photo_car'], caption=f"Телефон {data['phone']}")
    chat_admin = os.environ.get('CHAT_ID_ADMIN')
    await message.answer('Машина отправлена на рассмотрение')
    await bot.send_photo(chat_id=chat_admin,
                         photo=data['photo_car'],
                         caption=f'Ргеистрация автомобиля\n\n'
                                 f'Телефон:<b> {data["phone"]}</b>\n\n'
                                 f'Название машины: <b>{data["car_name"]}</b>\n\n'
                                 f'Номер машины: <b>{data["number_car"]}Р</b>',
                         reply_markup=await kb.add_car_or_no(driver_id))
    await state.clear()


@router.message(AddDrivercar.photo_car)
async def phone(message: Message, state: FSMContext):
    await message.answer('Отправь фото корректно')
