import os
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from dotenv import load_dotenv

from app.change_price import Settings
from filters.chat_type import ChatTypeFilter
from aiogram import Bot
import app.keyboards as kb
from app.database.requests import get_all_orders, get_driver, start_order_execution, delete_order_execution, \
    set_chat_id_driver, set_chat_id_user, update_driver

from middleware.driver_active_middleware import DriverActiveMiddleware

user_group_router = Router()
user_group_router.message.filter(ChatTypeFilter(['group', 'supergroup']))
load_dotenv()

# user_group_router.message.middleware(DriverActiveMiddleware())
user_group_router.callback_query.middleware(DriverActiveMiddleware())

@user_group_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f'{message.chat.id}')
@user_group_router.callback_query(F.data.startswith('accept_'))
async def accept(callback: CallbackQuery, bot: Bot, state: FSMContext):
    try:
        order_id = await get_all_orders(callback.data.split('_')[1])
        # message_id_pass = callback.data.split('_')[2]
        message_id_pass = order_id.chat_id_user
        driver = await get_driver(callback.from_user.id)
        if driver.price <= 0:
            await callback.answer(
                "Вы не можете принять заказ, так как у вас недостаточно средств на балансе.",
                show_alert=True
            )
            return
        await update_driver(callback.from_user.id, price=int(driver.price - int(order_id.price * 0.10)))
        await callback.message.edit_text(text=f'Номер заказа - <b><code>{order_id.id}</code></b>\n'
                                              f'Водитель {driver.name} принял заказ',
                                         reply_markup=await kb.go_to_order())
        # if not driver.active:
        #     await bot.send_message(chat_id=callback.from_user.id,
        #                            text=f"Вы не активны и не можете принимать заказы.\n"
        #                                 f"Нажмите /start и выйдите на линию")
        #     return

        # Создаем запись о начале выполнения заказа
        try:
            await start_order_execution(order_id.id, driver.id)
        # удаляю сообщение у пользователя
            await bot.delete_message(chat_id=order_id.user_rel.tg_id, message_id=message_id_pass)
        except TelegramBadRequest as e:
            if "message to delete not found" in str(e):
                # Логирование или обработка конкретного случая, если сообщение не найдено
                print("Сообщение уже удалено или не найдено.")
            else:
                raise e

        message_pass = await bot.send_photo(chat_id=order_id.user_rel.tg_id,
                                            photo=driver.photo_car,
                                            caption=f'🤝<b>ВАШ ЗАКАЗ ПРИНЯТ</b>\n'
                                                    f'👤{driver.name} на {driver.car_name}\n'
                                                    f'🚕Номер авто: {driver.number_car}\n'
                                                    f'📞Телефон: {driver.phone}\n'
                                                    f'💰Цена поездки: {order_id.price} руб\n')

        # Обновляем состояние, сохраняя идентификатор отправленного сообщения

        text_driver = (f"Заказ <b>{order_id.id}</b>\n\n"
                        f"Телефон <b>{order_id.user_rel.phone}</b>\n\n"
                        f"📍:<b>{order_id.city1_id} - {order_id.address1_id.upper()}</b>\n\n"
                        f"📍:<b>{order_id.city2_id} - {order_id.address2_id.upper()}</b>\n\n")
        if order_id.add_address:
            text_driver += f"🔃<b>{order_id.add_address}</b>\n\n"
        if order_id.add_new_address1:
            text_driver += f'📍: <b>{order_id.add_new_address1} - {order_id.add_street_address1.upper()}</b>\n\n'
        if order_id.add_new_address2:
            text_driver += f'📍: <b>{order_id.add_new_address2} - {order_id.add_street_address2.upper()}</b>\n\n'
        text_driver += (f"Цена: <b>{order_id.price}Р</b>\n\n"
                        f'⌚ Выберите время подачи: ⬇️')

        message_driver = await bot.send_message(chat_id=callback.from_user.id,
                                                text=text_driver,
                                                reply_markup=await kb.time_wait(order_id.id))
        # записываем в бд чат
        await set_chat_id_driver(order_id.id, message_pass.message_id)
        await set_chat_id_user(order_id.id, message_driver.message_id)

        await bot.edit_message_reply_markup(
            chat_id=order_id.user_rel.tg_id,
            message_id=message_pass.message_id,
            reply_markup=await kb.delete_order(order_id.id))



    except AttributeError:
        await callback.answer('')
        await callback.message.edit_text('Пассажир отменил заказ')
