import os

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, or_f, Command
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup, StateFilter
from aiogram import Bot

from aiogram_dialog import Dialog, DialogManager, Window, StartMode, ShowMode

from dotenv import load_dotenv

import app.keyboards as kb
import app.kb.kb_admin as kb_ad

from app.change_price import Settings
from app.dialog.states import StartOrder, AddUser, AddOrder
from app.database.requests import set_user, get_user, add_car, shop_add, get_order_driver, delete_order_pass, \
    update_driver
from app.dialog_info.info_dialogs import Information
from filters.chat_type import ChatTypeFilter
from middleware.ban_middleware import CheckUserBannedMiddleware
from middleware.shop_middleware import ShopMiddleware
from middleware.user_check_middleware import UserCheckMiddleware

router = Router()
router.message.filter(ChatTypeFilter(['private']))

router.message.middleware(CheckUserBannedMiddleware())
router.message.middleware(ShopMiddleware())
# router.message.middleware(UserCheckMiddleware())

load_dotenv()


@router.callback_query(F.data == 'neworder')
async def on_new_order(callback: CallbackQuery, dialog_manager: DialogManager):
    # Запуск диалога при нажатии на кнопку "neworder"
    await callback.answer('')
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.message.answer('Пройдите повторно регистрацию. Нажмите /start')
        return
    await dialog_manager.start(AddOrder.city1, mode=StartMode.RESET_STACK)


# ----------------Отменить заказ---------------
@router.message(F.text == 'Отменить')
async def cancel_order_reply(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(f'Вы отменили заказ. Нажмитке /start чтоб начать поездку', reply_markup=ReplyKeyboardRemove())


# ----------------Отменить заказ---------------
@router.callback_query(F.data.startswith('cancelorder_'))
async def cancelorder(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.clear()
    await callback.message.delete()

    await callback.message.answer(f'Вы отменили')


@router.message(CommandStart())
async def cmd_start(message: Message,
                    dialog_manager: DialogManager,
                    state: FSMContext):
    # Запуск диалога при нажатии на кнопку "neworder"
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user:
        await dialog_manager.start(StartOrder.user, mode=StartMode.RESET_STACK)
    else:
        await message.answer(f'Добро пожаловать в такси городок!\n'
                             f'Пожалуйста, отправьте свой номер телефона для регистрации c помощью кнопки:',
                             reply_markup=await kb.phone())
        await state.set_state(StartOrder.request_phone)


# Обработка полученного номера телефона
@router.message(StartOrder.request_phone, F.contact)
async def process_phone(message: Message, state: FSMContext, dialog_manager: DialogManager):
    # Обработка полученного номера телефона
    phone_number = message.contact.phone_number
    if not phone_number.startswith("+"):
        phone_number = "+" + phone_number
    tg_id = message.from_user.id

    # Запись пользователя в базу данных
    await set_user(tg_id, phone_number)

    # Приветствие пользователя после успешной записи
    await message.answer(f'Вы зарегестрировались',
                         reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await dialog_manager.start(StartOrder.user, mode=StartMode.RESET_STACK)


@router.message(StartOrder.request_phone)
async def process_invalid_phone(message: Message):
    # Обработка случая, когда пользователь отправляет что-то, кроме номера телефона
    await message.answer('Пожалуйста, используйте кнопку для отправки телефона')


# ---- отменить заказ----
@router.callback_query(F.data.startswith('deleteorder_'))
async def delete_order_passager(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer('')
    order_id = callback.data.split('_')[1]
    driver_id = await get_order_driver(order_id)
    message_id_driver = driver_id.chat_id_driver
    message_id = driver_id.chat_id_user
    if driver_id.drivers_reply:
        driver = driver_id.drivers_reply[0]
        await update_driver(driver.tg_id, price=int(driver.price + int(driver_id.price * 0.10)))
        await bot.edit_message_text(chat_id=driver.tg_id,
                                    message_id=message_id_driver,
                                    text=f"Заказ <code>{driver_id.id}</code>\n"
                                         f"<b>❌Пассажир отменил заказ</b>\n\n"
                                         f"Телефон <b>{driver_id.user_rel.phone}</b>")
        await callback.message.delete()

        await callback.message.answer(f'Заказ отменен')

        await delete_order_pass(order_id)
        await state.clear()
        return
    else:
        await bot.edit_message_text(chat_id=os.getenv('CHAT_GROUP_ID'),
                                    message_id=message_id_driver,
                                    text=f"Заказ <code>{driver_id.id}</code>\n"
                                         f"<b>❌Пассажир отменил заказ</b>\n\n"
                                         f"Телефон <b>{driver_id.user_rel.phone}</b>")
        try:
            await callback.message.delete()
        except TelegramBadRequest as e:
            if "message to delete not found" not in str(e):
                print(f"Ошибка при удалении сообщения: {e}")

        # Отправляем подтверждение отмены
        await callback.message.answer(f'Заказ отменен')
        await state.clear()
        return


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
                               text=f'CHAT ID: <b>"{message.from_user.id}"</b>\n'
                                    f'Пользователь ник нейм: <b>@{message.from_user.username}</b>\n'
                                    f'Имя: <b>{message.from_user.first_name}</b>\n'
                                    f'Телефон: <b>{user.phone}</b>\n'
                                    f'------------------------------\n'
                                    f'Сообщение:\n'
                                    f'<i>{message.text}</i>\n',
                               reply_markup=await kb_ad.send_to_user())

        await state.clear()
        await message.answer('Спасибо за сообщение. В скором времени с вами свяжется менеджер')
                             #reply_markup=await kb.main())

    # elif message.voice:
    #     await state.update_data(send_manager=message.voice)
    #     await bot.send_voice(chat_id=os.getenv('CHAT_ID_ADMIN'),
    #                          caption=f'CHAT ID: <b>"{message.from_user.id}"</b>\n'
    #                                  f'Пользователь ник нейм: <b>@{message.from_user.username}</b>\n'
    #                                  f'Имя: <b>{message.from_user.first_name}</b>\n'
    #                                  f'Телефон: <b>+{user.phone}</b>\n',
    #                          voice=message.voice.file_id,
    #                          reply_markup=await kb_ad.send_to_user())
    #     await state.clear()
    #     await message.answer('Спасибо за голосовое сообщение. В скором времени с вами свяжется менеджер',
    #                          reply_markup=await kb.main())
    else:
        await message.answer('Отправь текстовое сообщение')


class AddDrivercar(StatesGroup):
    phone = State()
    name = State()
    car_name = State()
    number_car = State()
    photo_car = State()


@router.message(Command('add_car'))
async def add_phone1(message: Message, state: FSMContext):
    await state.set_state(AddDrivercar.phone)
    await message.answer('Отправь номер телефона с помощью кнопки', reply_markup=await kb.phone())


@router.message(AddDrivercar.phone, F.contact)
async def add_name(message: Message, state: FSMContext):
    phone_number = message.contact.phone_number
    if not phone_number.startswith("+"):
        phone_number = "+" + phone_number
    await state.update_data(phone=phone_number)
    await state.set_state(AddDrivercar.name)
    await message.answer('Как зовут водителя', reply_markup=await kb.cancel_order())


@router.message(AddDrivercar.phone)
async def add_phone2(message: Message, state: FSMContext):
    await message.answer('Отправь телефон через кнопку')


@router.message(AddDrivercar.name, F.text)
async def add_car_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddDrivercar.car_name)
    await message.answer('Введите название марки машины', reply_markup=await kb.cancel_order())


@router.message(AddDrivercar.name)
async def add_phone2(message: Message, state: FSMContext):
    await message.answer('Отправь как зовут водителя')


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
    await message.answer('Машина отправлена на рассмотрение', reply_markup=ReplyKeyboardRemove())
    await bot.send_photo(chat_id=chat_admin,
                         photo=data['photo_car'],
                         caption=f'Ргеистрация автомобиля\n\n'
                                 f'Телефон:<b> {data["phone"]}</b>\n\n'
                                 f'Имя:<b> {data["name"]}</b>\n\n'
                                 f'Название машины: <b>{data["car_name"]}</b>\n\n'
                                 f'Номер машины: <b>{data["number_car"]}</b>',
                         reply_markup=await kb.add_car_or_no(driver_id))
    await state.clear()


@router.message(AddDrivercar.photo_car)
async def phone(message: Message, state: FSMContext):
    await message.answer('Отправь фото корректно')


class AddShop(StatesGroup):
    shop_name = State()


@router.message(Command('add_shop'))
async def add_shop(message: Message, state: FSMContext):
    await state.set_state(AddShop.shop_name)
    await message.answer('Напишите название магазина', reply_markup=await kb.cancel_order())


@router.message(AddShop.shop_name, F.text)
async def add_shop(message: Message, state: FSMContext):
    if message.text:
        data = await state.update_data(shop_name=message.text)
        user_id = message.from_user.id
        await shop_add(user_id, shop_activate=True, shop_name=data['shop_name'])
        await message.answer('Магазин успешно добавлен', reply_markup=ReplyKeyboardRemove())
        await state.clear()
    else:
        await message.answer('Введите корретно название магазина')


@router.message(Command('info'))
async def cmd_start(message: Message,
                    dialog_manager: DialogManager,
                    state: FSMContext):
    # Запуск диалога при нажатии на кнопку "info"
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user:
        await dialog_manager.start(state=Information.info_np,
                                   mode=StartMode.RESET_STACK)
    else:
        await message.answer(f'Добро пожаловать в такси городок!\n'
                             f'Пожалуйста, отправьте свой номер телефона для регистрации c помощью кнопки:',
                             reply_markup=await kb.phone())
        await state.set_state(StartOrder.request_phone)