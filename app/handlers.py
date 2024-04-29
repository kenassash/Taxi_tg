from aiogram import Router, F
from aiogram.handlers import CallbackQueryHandler
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup, StateFilter
from haversine import haversine, Unit
from aiogram import Bot

import app.keyboards as kb
from app.geolocation import coords_to_address, addess_to_coords
from app.database.requests import set_user, set_order, get_all_orders
from filters.chat_type import ChatTypeFilter
from app.calculate import length_way


router = Router()
router.message.filter(ChatTypeFilter(['private']))
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
async def cmd_start(message: Message):
    await set_user(message.from_user.id)
    full_name = message.from_user.full_name
    await message.answer(f'<b>Добро пожаловать {full_name} </b>😊', reply_markup=kb.main)



@router.callback_query(StateFilter(None), F.data == 'neworder')
async def neworder(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.edit_text(
        f'<b>🅰️: Откуда поедите ❓\n🖋️Напишите улицу и № дома\n\nили\n\nотправьте геолокацию</b>')
    await state.set_state(AddOrder.point_start)


@router.message(AddOrder.point_start, F.text)
async def point_starter(message: Message, state: FSMContext):
    address_go = message.text
    print(address_go)
    try:
        longitude_end, latitude_end, trimmed_string = await addess_to_coords(address_go)
        print(trimmed_string)
        print(float(longitude_end), float(latitude_end))
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
    await message.answer(f'<b>🅰️: {point} \n📍----\n\n🅱️: Куда едем?\n️Напишите улицу и № дома</b>')
    await state.set_state(AddOrder.point_end)


@router.message(AddOrder.point_start)
async def point_start(message: Message, state: FSMContext):
    await message.answer(f'Введите корреткно от куда едите')


@router.message(AddOrder.point_end, F.text)
async def phone(message: Message, state: FSMContext):
    address_go = message.text
    try:
        longitude_end, latitude_end, trimmed_string = await addess_to_coords(address_go)
        print(trimmed_string)
        print(longitude_end, latitude_end)
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
async def phone(message: Message, state: FSMContext):
    await message.answer('Введите корреткно куда едите')


@router.message(AddOrder.phone, F.contact)
async def phone(message: Message, state: FSMContext,  bot: Bot):
    await state.update_data(phone=message.contact.phone_number, tg_id=message.from_user.id)
    data = await state.get_data()
    distance, time_way, price = await length_way(data['coordinat_start_x'],
                          data['coordinat_start_y'],
                          data['coordinat_end_x'],
                          data['coordinat_end_y'])

    await state.update_data(distance=distance, time_way=time_way, price=price)
    data = await state.get_data()
    order_id = await set_order(data)

    await message.answer(f"<i><b>Ваш заказ.</b></i>\n\n"
                         f"<i><b>Начальная точка:</b></i> {data['point_start']}\n\n"
                         f"<i><b>Конечная точка:</b></i> {data['point_end']}\n\n"
                         f"<i><b>Расстояние:</b></i> {distance}км\n\n"
                         f"<i><b>Время пути:</b></i> {time_way}мин\n\n"
                         f"<b>Цена:</b> {price}₽",
                         reply_markup=ReplyKeyboardRemove())
    order_data = await get_all_orders(order_id)
    await bot.send_message(chat_id=-1002080907384,
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
