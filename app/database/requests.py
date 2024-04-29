from app.database.models import User, Order, Driver
from app.database.models import async_session

from sqlalchemy import select, update, delete


async def set_user(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if not user:
            session.add(User(tg_id=tg_id))
            await session.commit()

async def set_order(data):
    async with async_session() as session:
        order = Order(**data)
        session.add(order)
        await session.commit()  # Сохраняем изменения в базу данных
        await session.refresh(order)  # Обновляем объект, чтобы получить актуальный id
        return order.id


async def get_all_orders(id):
     async with async_session() as session:
         result = await session.scalar(select(Order).where(Order.id == id))
         return result

async def add_car(data):
    async with async_session() as session:
        session.add(Driver(**data))
        await session.commit()