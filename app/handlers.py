import os

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, or_f, Command
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup, StateFilter
from aiogram import Bot
from dotenv import load_dotenv

import app.keyboards as kb
import app.keyboard_city as kb_city
from app.change_price import Settings
from app.geolocation import coords_to_address, addess_to_coords
from app.database.requests import set_user, set_order, get_all_orders, get_driver, active_driver, get_user, add_car, \
    delete_order_pass, get_order_driver
from filters.chat_type import ChatTypeFilter
from app.calculate import length_way
from utils.paginator import Paginator

router = Router()
router.message.filter(ChatTypeFilter(['private']))
load_dotenv()


# ----------------Отменить заказ---------------
@router.message(F.text == 'Отменить')
async def cancel_order_reply(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(f'Вы отменили заказ. Нажмитке /start чтоб начать поездку', reply_markup=ReplyKeyboardRemove())


@router.callback_query(StateFilter('*'), F.data == 'backbutton_')
async def backbutton(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    previous = None
    for step in AddOrder.__all_states__:
        if step.state == 'AddOrder:address1':
            await state.set_state(previous)
            await callback.answer('')
            await callback.message.edit_text(f'Вы вернулись к прошлому шагу\n\n{AddOrder.texts[previous.state]}\n',
                                             reply_markup=await kb_city.keyboard_city1())
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
    city1 = State()
    address1 = State()
    city2 = State()
    address2 = State()

    texts = {
        'AddOrder:city1': 'Выберите кнопку от куда поедите',
        'AddOrder:address1': 'Напишите адрес куда поедите',
        'AddOrder:city2': 'Выберите кнопку куда поедите',
        'AddOrder:address2': 'Напишите адрес от куда поедите',

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
async def neworder(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await callback.message.edit_text(
        f'<b>🅰️: Выберите населенный пункт от куда поедите:</b>',
        reply_markup=await kb_city.keyboard_city1())
    await state.set_state(AddOrder.city1)


@router.callback_query(AddOrder.city1, or_f(F.data.startswith('cities1_'),
                                            F.data.startswith('citiesoutside1_')))
async def city1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    if callback.data.startswith('citiesoutside1_'):
        await callback.message.edit_text(
            f'<b>🅰️: Выберите населенный пункт от куда поедите:</b>',
            reply_markup=await kb_city.keyboard_city3())
        await state.set_state(AddOrder.city1)
        return

    city1 = callback.data.split('_')[1]
    price1 = callback.data.split('_')[2]
    await state.update_data(city1=city1, price1=price1)
    await callback.message.edit_text(
        f'<b>🅰️: Напишите  Улицу и № дома\n'
        f'Например: Южная 8</b>',
        reply_markup=await kb.cancel_order())
    await state.set_state(AddOrder.address1)


@router.message(AddOrder.city1)
async def city2(message: Message, state: FSMContext):
    await message.answer('Выберите кнопку населенного пункта')


@router.message(AddOrder.address1, F.text)
async def address1(message: Message, state: FSMContext):
    await state.update_data(address1=message.text)
    data = await state.get_data()
    await message.answer(f'<b>🅰️: {data["city1"]} - {data["address1"]}\n\n'
                         f'🅱️: Выберите населенный пункт куда поедите:</b>',
                         reply_markup=await kb_city.keyboard_city2())
    await state.set_state(AddOrder.city2)


@router.message(AddOrder.address1)
async def address1(message: Message, state: FSMContext):
    await message.answer('Напишите адрес от куда поедите')


@router.callback_query(AddOrder.city2, or_f(F.data.startswith('cities2_'),
                                            F.data.startswith('citiesoutside2_')))
async def city2(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    if callback.data.startswith('citiesoutside2_'):
        data = await state.get_data()
        await callback.message.edit_text(f'<b>🅰️: {data["city1"]} - {data["address1"]}\n\n'
                             f'🅱️: Выберите населенный пункт куда поедите:</b>',
                             reply_markup=await kb_city.keyboard_city4())
        await state.set_state(AddOrder.city2)
        return
    city2 = callback.data.split('_')[1]
    price2 = callback.data.split('_')[2]
    await state.update_data(city2=city2, price2=price2)
    await callback.message.edit_text(
        f'<b>🅱️: Напишите  Улицу и № дома\n'
        f'Например: Ленина 60</b>',
        reply_markup=await kb.cancel_order())
    await state.set_state(AddOrder.address2)


@router.message(AddOrder.city2)
async def city2(message: Message, state: FSMContext):
    await message.answer('Выберите кнопку населенного пункта')


@router.message(AddOrder.address2, F.text)
async def address2(message: Message, state: FSMContext):
    await state.update_data(address2=message.text)
    data = await state.get_data()
    point_start = f'{data["city1"]} - {data["address1"]}'
    point_end = f'{data["city2"]} - {data["address2"]}'

    price1 = data['price1']
    price2 = data['price2']
    print(type(price1), type(price2))
    price_max = max(int(price1), int(price2))
    price = int(price_max) + Settings.fix_price
    await message.answer(f"🅰️: Начальная точка: <b>{point_start}</b>\n\n"
                         f"🅱️: Конечная точка: <b>{point_end}</b>\n\n"
                         f"<b>Цена:</b> {price}₽",
                         reply_markup=await kb.order_now())


@router.message(AddOrder.address2)
async def address2(message: Message):
    await message.answer('Напишите адрес куда поедите')


@router.callback_query(F.data == 'order_now')
async def finish_price(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer('')
    data = await state.get_data()

    point_start = f'{data["city1"]} - {data["address1"]}'
    point_end = f'{data["city2"]} - {data["address2"]}'

    price1 = data['price1']
    price2 = data['price2']
    price_max = max(price1, price2)
    price = int(price_max) + Settings.fix_price

    await state.clear()
    await state.update_data(point_start=point_start, point_end=point_end, price=price)
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
                                     f"Цена: <b>{order_data.price}Р</b>",
                                     reply_markup=await kb.delete_order(order_id))

    await state.clear()


@router.callback_query(F.data.startswith('deleteorder_'))
async def delete_order_passager(callback: CallbackQuery, bot: Bot):
    await callback.answer('')
    order_id = callback.data.split('_')[1]
    driver_id = await get_order_driver(order_id)
    if driver_id is not None:
        await bot.send_message(chat_id=driver_id.tg_id, text='Пассажир отменил заказ')
    await delete_order_pass(order_id)
    await callback.message.edit_text('Заказ отменен')


# -------------отправка сообщения администраторам\менеджерам
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
                               text=f'Пользователь ник нейм: <b>@{message.from_user.username}</b>\n'
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
                             caption=f'Пользователь ник нейм: <b>@{message.from_user.username}</b>\n'
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
