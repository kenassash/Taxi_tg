from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.database.requests import add_car

import app.keyboards as kb

admin = Router()

class AddDriver(StatesGroup):
    phone = State()
    car_name = State()
    number_car = State()
    photo_car = State()


class AdminProtect(Filter):
    async def __call__(self, message:Message):
        return message.from_user.id in [216159472]

@admin.message(AdminProtect(), Command('add_car'))
async def add_phone(message: Message, state: FSMContext):
    await state.set_state(AddDriver.phone)
    await message.answer('Отправь телефон', reply_markup=await kb.phone())

@admin.message(AdminProtect(), AddDriver.phone, F.contact)
async def add_car_name(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(AddDriver.car_name)
    await message.answer('Введите название марки машины', reply_markup=ReplyKeyboardRemove())

@admin.message(AddDriver.phone)
async def add_phone(message: Message, state: FSMContext):
    await message.answer('Отправь телефон через кнопку')



@admin.message(AdminProtect(), AddDriver.car_name, F.text)
async def add_number_car(message: Message, state: FSMContext):
    await state.update_data(car_name=message.text)
    await state.set_state(AddDriver.number_car)
    await message.answer('Введите гос номер машины')

@admin.message(AddDriver.car_name)
async def add_car_name(message: Message, state: FSMContext):
    await message.answer('Введите коррекно название машины')




@admin.message(AdminProtect(), AddDriver.number_car, F.text)
async def add_item_category(message: Message, state: FSMContext):
    await state.update_data(number_car=message.text)
    await state.set_state(AddDriver.photo_car)
    await message.answer('Отправь фото машины')

@admin.message(AddDriver.number_car)
async def phone(message: Message, state: FSMContext):
    await message.answer('Отправь коррекно гос номер')


@admin.message(AdminProtect(), AddDriver.photo_car, F.photo)
async def add_item_category(message: Message, state: FSMContext):
    await state.update_data(photo_car=message.photo[-1].file_id, tg_id=message.from_user.id)
    data = await state.get_data()
    await message.answer(str(data))
    await add_car(data)
    await message.answer('Машина успешна добавлена')
    await state.clear()

@admin.message(AddDriver.photo_car)
async def phone(message: Message, state: FSMContext):
    await message.answer('Отправь фото корректно')