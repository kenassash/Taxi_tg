import os
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from dotenv import load_dotenv

from app.database.requests import get_all_orders, get_driver, delete_order_execution, delete_order_pass, \
    get_order_driver, get_user, set_order
from filters.chat_type import ChatTypeFilter
import app.keyboards as kb

shop_router = Router()
shop_router.message.filter(ChatTypeFilter(['private']))
load_dotenv()


@shop_router.callback_query(F.data == 'shoporder')
async def shop_add_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.update_data(price=200)
    await state.clear()
    user_id = await get_user(callback.from_user.id)
    order_id = await set_order(user_id.id, data)
    order_data = await get_all_orders(order_id)

    sent_driver_message = await callback.message.edit_text(f"<b>Ожидайте водителя⌛</b>",
                                                           reply_markup=await kb.delete_order(order_id))

    sent_message = await bot.send_message(chat_id=os.getenv('CHAT_GROUP_ID'),
                                          text=f"Магазин <b>{user_id.shop_name}</b> доставка",
                                          reply_markup=await kb.accept(order_id, sent_driver_message.message_id))
    await state.clear()
    await state.update_data(message_id=sent_message.message_id)