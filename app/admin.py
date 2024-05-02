import os

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database.requests import add_car, get_all_car, remove_car

import app.keyboards as kb
from filters.chat_type import ChatTypeFilter, IsAdmin

admin = Router()
admin.message.filter(ChatTypeFilter(["private"]), IsAdmin())



class AddDriver(StatesGroup):
    phone = State()
    car_name = State()
    number_car = State()
    photo_car = State()
    tg_id = State()

# class AdminProtect(Filter):
#     async def __call__(self, message: Message):
#         return message.from_user.id in [216159472]



@admin.message(IsAdmin(),Command("admin"))
async def admin_features(message: Message):
    await message.answer("Что хотите сделать?", reply_markup=await kb.admin_keyboard())

# ------------------Добавить машину /add_car-----------------------

@admin.callback_query(IsAdmin(), F.data == 'add_car')
async def add_phone1(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddDriver.phone)
    await callback.answer('')
    await callback.message.answer('Отправь номер телефона', reply_markup=await kb.cancel_order())


@admin.message(IsAdmin(), AddDriver.phone, F.text)
async def add_car_name(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(AddDriver.car_name)
    await message.answer('Введите название марки машины', reply_markup=await kb.cancel_order())


@admin.message(AddDriver.phone)
async def add_phone2(message: Message, state: FSMContext):
    await message.answer('Отправь телефон через кнопку')


@admin.message(IsAdmin(), AddDriver.car_name, F.text)
async def add_number_car(message: Message, state: FSMContext):
    await state.update_data(car_name=message.text)
    await state.set_state(AddDriver.number_car)
    await message.answer('Введите гос номер машины', reply_markup=await kb.cancel_order())


@admin.message(AddDriver.car_name)
async def add_car_name(message: Message, state: FSMContext):
    await message.answer('Введите коррекно название машины')


@admin.message(IsAdmin(), AddDriver.number_car, F.text)
async def add_item_category(message: Message, state: FSMContext):
    await state.update_data(number_car=message.text)
    await state.set_state(AddDriver.tg_id)
    await message.answer('Отправь CHAT-ID пользователя', reply_markup=await kb.cancel_order())


@admin.message(AddDriver.number_car)
async def add_number_car(message: Message, state: FSMContext):
    await message.answer('Отправь коррекно гос номер')


@admin.message(IsAdmin(), AddDriver.tg_id, F.text)
async def add_tg_id(message: Message, state: FSMContext):
    await state.update_data(tg_id=message.text)
    await state.set_state(AddDriver.photo_car)
    await message.answer('Отправь фото машины', reply_markup=await kb.cancel_order())


@admin.message(AddDriver.tg_id)
async def add_tg_id(message: Message, state: FSMContext):
    await message.answer('Отправь корректно chat-id')


@admin.message(IsAdmin(), AddDriver.photo_car, F.photo)
async def add_item_category(message: Message, state: FSMContext):
    await state.update_data(photo_car=message.photo[-1].file_id)
    data = await state.get_data()
    await message.answer_photo(photo=data['photo_car'], caption=f"Телефон {data['phone']}")
    await add_car(data)
    await message.answer('Машина успешна добавлена')
    await state.clear()


@admin.message(AddDriver.photo_car)
async def phone(message: Message, state: FSMContext):
    await message.answer('Отправь фото корректно')


# ------------------Удалить машину /delete_car-----------------------
@admin.callback_query(IsAdmin(), F.data == 'delete_car')
async def delete_car_message(callback: CallbackQuery):
    await callback.answer('')
    drivers = await get_all_car()
    for driver in drivers:
        await callback.message.answer_photo(photo=driver.photo_car)
        await callback.message.answer(f"{driver.phone}\n{driver.car_name}\n{driver.number_car}\n",
                             reply_markup=await kb.delete_car(driver.id))


@admin.callback_query(IsAdmin(), F.data.startswith('deletecar_'))
async def delete_car_callback(callback: CallbackQuery):
    await callback.answer('')
    await remove_car(callback.data.split('_')[1])
    print(callback.data.split('_')[1])
    await callback.message.edit_text('Машина успешно удалена')


# ------------------Удалить машину /delete_car-----------------------
