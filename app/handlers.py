import os
import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, or_f
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup, StateFilter
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
    tg_id = State()
    point_start = State()
    point_end = State()
    phone = State()

    coordinat_start_x = State()
    coordinat_start_y = State()
    coordinat_end_x = State()
    coordinat_end_y = State()

    texts = {
        'AddOrder:point_start': 'Введите начальную точку заново',
        'AddOrder:point_end': 'Введите конечную точку заново',
        'AddOrder:phone': 'Введите телефон заново'
    }


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if state.set_state():
        await state.clear()

# проверка если таксист
    drivers = await get_driver(message.from_user.id)
    if drivers and drivers.tg_id == message.from_user.id:
        await message.answer(f'<b>Добро пожаловать Таксист {message.from_user.full_name}</b>😊\n\n',
                             reply_markup=await kb.driver_start_or_finish())
        return

    await set_user(message.from_user.id)
    full_name = message.from_user.full_name
    await message.answer(f'<b>Добро пожаловать {full_name} </b>😊', reply_markup=kb.main)


@router.callback_query(StateFilter(None), F.data == 'neworder')
async def neworder(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer('')
    await callback.message.edit_text(
        f'<b>🅰️: Напишите  Улицу и № дома\n'
        f'Например: Южная 8</b>',
        reply_markup=await kb.cancel_order())
    await state.set_state(AddOrder.point_start)


@router.message(AddOrder.point_start, (F.text | F.local))
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
        await message.answer('Улица и дом не корретно введены')
        await state.clear()
        full_name = message.from_user.full_name
        await message.answer(f'<b>Добро пожаловать {full_name} </b>😊', reply_markup=kb.main)
        return

    await state.update_data(point_start=trimmed_string,
                            coordinat_start_x=float(longitude_end),
                            coordinat_start_y=float(latitude_end))
    data = await state.get_data()
    point = data.get('point_start')
    await message.answer(f'<b>🅰️: {point}\n\n'
                         f'🅱️: Напишите куда поедите?\nНапример: Ленина 60;</b>',
                         reply_markup=await kb.back_button())
    await state.set_state(AddOrder.point_end)


@router.callback_query(AddOrder.point_start)
async def point_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(f'Введите корреткно от куда едите')


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
    data = await state.get_data()
    point = data.get('point_start')
    end = data.get('point_end')
    await message.answer(f'<b>🅰️: {point}\n\n'
                         f'🅱️: {end}\n\n'
                         f'Укажите ваш номер телефона</b>',
                         reply_markup=await kb.back_button())
    # await message.answer('Отправь телефон', reply_markup=await kb.phone())



@router.message(AddOrder.point_end)
async def point_end(message: Message, state: FSMContext):
    await message.answer('Введите корреткно куда едите')


@router.message(AddOrder.phone)
async def phone(message: Message, state: FSMContext, bot: Bot):
    if(re.findall('^\+?[7][-\(]?\d{3}\)?-?\d{3}-?\d{2}-?\d{2}$', message.text)):
        await state.update_data(phone=message.text, tg_id=message.from_user.id)
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
    else:
        await bot.send_message(message.from_user.id, f"Номер указан не верно")


@router.message(AddOrder.phone)
async def phone(message: Message, state: FSMContext):
    await message.answer('Отправь корректно телефон')




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
