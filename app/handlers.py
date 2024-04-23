from aiogram import Router, F
from aiogram.handlers import CallbackQueryHandler
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup, StateFilter

import app.keyboards as kb
from app.geolocation import coords_to_address, addess_to_coords
from app.database.requests import set_user, set_order

router = Router()
class AddOrder(StatesGroup):
    point_start = State()
    point_end = State()
    phone = State()


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
        longitude_end, latitude_end = [float(x) for x in addess_to_coords(address_go).split(' ')]
    except IndexError:
        await message.answer('Улица и дом не корретно')
        await state.clear()
        full_name = message.from_user.full_name
        await message.answer(f'<b>Добро пожаловать {full_name} </b>😊', reply_markup=kb.main)
        return
    print(longitude_end, latitude_end)

    await state.update_data(point_start=message.text)
    data = await state.get_data()
    point = data.get('point_start')
    await message.answer(f'<b>🅰️: {point} \n📍----\n\n🅱️: Куда едем?\n️Напишите улицу и № дома</b>')
    await state.set_state(AddOrder.point_end)


@router.message(AddOrder.point_start)
async def point_starter(message: Message, state: FSMContext):
    await message.answer(f'Введите корреткно от куда едите')


@router.message(AddOrder.point_end, F.text)
async def phone(message: Message, state: FSMContext):
    await state.update_data(point_end=message.text)
    await state.set_state(AddOrder.phone)
    await message.answer('Отправь телефон', reply_markup=await kb.phone())


@router.message(AddOrder.point_end)
async def phone(message: Message, state: FSMContext):
    await message.answer('Введите корреткно куда едите')


@router.message(AddOrder.phone, F.contact)
async def phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    data = await state.get_data()
    await set_order(data)
    await message.answer(str(data))
    await message.answer('Товар успешно добавлен', reply_markup=ReplyKeyboardRemove())
    await state.clear()


@router.message(AddOrder.phone)
async def phone(message: Message, state: FSMContext):
    await message.answer('Отправь телефон через кнопку')
