import os

from aiogram import Router, F
from aiogram.handlers import CallbackQueryHandler
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup, StateFilter
from haversine import haversine, Unit
from aiogram import Bot
from dotenv import load_dotenv

import app.keyboards as kb
from app.geolocation import coords_to_address, addess_to_coords
from app.database.requests import set_user, set_order, get_all_orders, get_driver, active_driver
from filters.chat_type import ChatTypeFilter
from app.calculate import length_way

router = Router()
router.message.filter(ChatTypeFilter(['private']))
load_dotenv()


class AddOrder(StatesGroup):
    tg_id = State()
    point_start = State()
    point_end = State()
    phone = State()

    coordinat_start_x = State()
    coordinat_start_y = State()
    coordinat_end_x = State()
    coordinat_end_y = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if state.set_state():
        await state.clear()

    drivers = await get_driver(message.from_user.id)
    if drivers.tg_id == message.from_user.id:
        await message.answer(f'<b>Добро пожаловать Таксист {message.from_user.full_name}</b>😊',
                             reply_markup=await kb.driver_start_or_finish())
        return

    await set_user(message.from_user.id)
    full_name = message.from_user.full_name
    await message.answer(f'<b>Добро пожаловать {full_name} </b>😊', reply_markup=kb.main)


@router.callback_query(StateFilter(None), F.data == 'neworder')
async def neworder(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.answer(
        f'<b>🅰️: Откуда поедите ❓\n🖋️Напишите улицу и № дома\n\nили\n\nотправьте геолокацию</b>',
        reply_markup=await kb.geolocate_point_start())
    await state.set_state(AddOrder.point_start)


@router.message(AddOrder.point_start, (F.text | F.location))
async def point_starter(message: Message, state: FSMContext):
    try:
        if message.text:
            address_go = message.text
            longitude_end, latitude_end, trimmed_string = await addess_to_coords(address_go)
            print(trimmed_string)
            print(float(longitude_end), float(latitude_end))
        elif message.location:
            latitude_end = message.location.latitude
            longitude_end = message.location.longitude
            trimmed_string = await coords_to_address(longitude_end, latitude_end)
            print(float(longitude_end), float(latitude_end))
            print(trimmed_string)

    except IndexError:
        await message.answer('Улица и дом не корретно')
        await state.clear()
        full_name = message.from_user.full_name
        await message.answer(f'<b>Добро пожаловать {full_name} </b>😊', reply_markup=kb.main)
        return

    await state.update_data(point_start=trimmed_string,
                            coordinat_start_x=float(longitude_end),
                            coordinat_start_y=float(latitude_end))
    data = await state.get_data()
    point = data.get('point_start')
    await message.answer(f'<b>🅰️: {point} \n📍----\n\n🅱️: Куда едем?\n️Напишите улицу и № дома</b>',
                         reply_markup=await kb.cancel_order())
    await state.set_state(AddOrder.point_end)


@router.message(AddOrder.point_start)
async def point_start(message: Message, state: FSMContext):
    await message.answer(f'Введите корреткно от куда едите')


@router.message(AddOrder.point_end, (F.text | F.location))
async def point_end(message: Message, state: FSMContext):
    try:
        if message.text:
            address_go = message.text
            longitude_end, latitude_end, trimmed_string = await addess_to_coords(address_go)
            print(trimmed_string)
            print(float(longitude_end), float(latitude_end))
        elif message.location:
            latitude_end = message.location.latitude
            longitude_end = message.location.longitude
            trimmed_string = await coords_to_address(longitude_end, latitude_end)
            print(float(longitude_end), float(latitude_end))
            print(trimmed_string)
    except IndexError:
        await message.answer('Улица и дом не корретно')
        await state.clear()
        full_name = message.from_user.full_name
        await message.answer(f'<b>Добро пожаловать {full_name} </b>😊', reply_markup=kb.main)
        return
    await state.update_data(point_end=trimmed_string,
                            coordinat_end_x=float(longitude_end),
                            coordinat_end_y=float(latitude_end))
    await state.set_state(AddOrder.phone)
    await message.answer('Отправь телефон', reply_markup=await kb.phone())


@router.message(AddOrder.point_end)
async def point_end(message: Message, state: FSMContext):
    await message.answer('Введите корреткно куда едите')


@router.message(AddOrder.phone, F.contact)
async def phone(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(phone=message.contact.phone_number, tg_id=message.from_user.id)
    data = await state.get_data()
    distance, time_way, price = await length_way(data['coordinat_start_x'],
                                                 data['coordinat_start_y'],
                                                 data['coordinat_end_x'],
                                                 data['coordinat_end_y'])

    await state.update_data(distance=distance, time_way=time_way, price=price)
    data = await state.get_data()
    order_id = await set_order(data)

    await message.answer(f"<i><b>Ожидайте ⌛</b></i>\n\n"
                         f"<i><b>Начальная точка:</b></i> {data['point_start']}\n\n"
                         f"<i><b>Конечная точка:</b></i> {data['point_end']}\n\n"
                         f"<i><b>Расстояние:</b></i> {distance}км\n\n"
                         f"<i><b>Время пути:</b></i> {time_way}мин\n\n"
                         f"<b>Цена:</b> {price}₽",
                         reply_markup=ReplyKeyboardRemove())
    order_data = await get_all_orders(order_id)
    await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                           text=f"<i><b>Заказ {order_id}</b></i>\n\n"
                                f"<i><b>Телефон {order_data.phone}</b></i>\n\n"
                                f"<i><b>Начальная точка:</b></i> {order_data.point_start}\n\n"
                                f"<i><b>Конечная точка:</b></i> {order_data.point_end}\n\n"
                                f"<i><b>Расстояние:</b></i> {order_data.distance}км\n\n"
                                f"<i><b>Время пути:</b></i> {order_data.time_way}мин\n\n"
                                f"<b>Цена:</b> {order_data.price}Р",
                           reply_markup=await kb.accept(order_id))
    await state.clear()


@router.message(AddOrder.phone)
async def phone(message: Message, state: FSMContext):
    await message.answer('Отправь телефон через кнопку')


@router.callback_query(F.data.startswith('cancelorder_'))
async def cancelorder(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(f'Вы отменили заказ. Нажмитке /start чтоб начать поездку')


@router.message(F.text.lower() == 'Отменить заказ')
async def cancelorder(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(f'Вы отменили заказ. Нажмитке /start чтоб начать поездку')


# ----------------Команды для Таксистов---------------
# ----------------Выйти на линию ---------------------
@router.callback_query(F.data.startswith('driverstart_'))
async def driver_start(callback: CallbackQuery):
    await callback.answer('')
    await active_driver(callback.message.chat.id, is_start=True)
    await callback.message.edit_text('Хорошо')

# ----------------Уйти с линии на линию ---------------------
@router.callback_query(F.data.startswith('driverfinish_'))
async def driver_finish(callback: CallbackQuery):
    await callback.answer('')
    await active_driver(callback.message.chat.id, is_start=False)
    await callback.message.edit_text('Плохо')
