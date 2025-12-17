import os
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from dotenv import load_dotenv

from app.change_price import Settings
from filters.chat_type import ChatTypeFilter
from aiogram import Bot
import app.keyboards as kb
from app.database.requests import get_all_orders, get_driver, start_order_execution, delete_order_execution, \
    set_chat_id_driver, set_chat_id_user, update_driver, get_all_active_drivers, get_next_available_driver, \
    increment_driver_order_count, mark_driver_inactive
from app.driver_activity_check import mark_driver_responded

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
        await set_chat_id_user(order_id.id, chat_id_driver=str(message_driver.message_id))

        await bot.edit_message_reply_markup(
            chat_id=order_id.user_rel.tg_id,
            message_id=message_pass.message_id,
            reply_markup=await kb.delete_order(order_id.id))



    except AttributeError:
        await callback.answer('')
        await callback.message.edit_text('Пассажир отменил заказ')


@user_group_router.callback_query(F.data.startswith("skip_"))
async def skip_order(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    await callback.answer('')

    try:
        # Получаем ID заказа из callback
        order_id = int(callback.data.split("_")[-1])
        current_driver_id = callback.from_user.id

        print(f"Водитель {current_driver_id} отказался от заказа {order_id}")

        # Убираем кнопки у текущего сообщения
        await callback.message.edit_reply_markup()

        order_data = await get_all_orders(order_id)
        if not order_data:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        # Формируем текст заказа - используем order_data, а не order_id
        text_order = (f"🔥Заказ <b>{order_data.id}</b>🔥\n\n"  # ← order_data.id
                      f"📞Телефон <b>{order_data.user_rel.phone}</b>\n\n"  # ← order_data.user_rel.phone
                      f"📍:<b>{order_data.city1_id} - {order_data.address1_id.upper()}</b>\n\n"  # ← order_data.city1_id
                      f"📍:<b>{order_data.city2_id} - {order_data.address2_id.upper()}</b>\n\n")  # ← order_data.city2_id

        if order_data.add_address:  # ← order_data.add_address
            text_order += f"🔃<b>{order_data.add_address}</b>\n\n"
        if order_data.add_new_address1:  # ← order_data.add_new_address1
            text_order += f"��:<b>{order_data.add_new_address1} - {order_data.add_street_address1.upper()}</b>\n\n"
        if order_data.add_new_address2:  # ← order_data.add_new_address2
            text_order += f"��:<b>{order_data.add_new_address2} - {order_data.add_street_address2.upper()}</b>\n\n"

        text_order += f"Цена: <b>{order_data.price}Р</b>"  # ← order_data.price

        # Получаем следующего доступного водителя
        next_driver = await get_next_available_driver()

        if not next_driver:
            # Если нет доступных водителей, уведомляем пассажира
            await bot.send_message(
                chat_id=order_data.user_rel.tg_id,
                text="К сожалению все водители отказались от заказа. Попробуйте позже."
            )
            return

        print(f"Следующий водитель: {next_driver.tg_id}")

        # Пытаемся отправить заказ следующему водителю
        try:
            message_id_driver = await bot.send_message(
                chat_id=next_driver.tg_id,
                text=text_order,
                reply_markup=await kb.accept_or_skip(order_id)
            )

            # Помечаем водителя как получившего заказ
            await increment_driver_order_count(next_driver.tg_id)

            # Обновляем данные заказа в базе
            from app.database.requests import set_chat_id_user
            await set_chat_id_user(order_id, driver_id=str(next_driver.tg_id),
                                   chat_id_driver=str(message_id_driver.message_id))

            print(f"Заказ {order_id} отправлен водителю {next_driver.tg_id}")

        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                print(f"Водитель {next_driver.tg_id} заблокировал бота")
                # Помечаем водителя как неактивного
                await mark_driver_inactive(next_driver.tg_id)
                # Пытаемся найти следующего водителя
                await skip_order(callback, bot, state)
                return
            else:
                raise e

    except Exception as e:
        print(f"Ошибка в skip_order: {e}")
        await callback.answer("Произошла ошибка при обработке отказа", show_alert=True)
