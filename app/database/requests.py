from app.database.models import User, Order
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
        session.add(Order(**data))
        await session.commit()


async def get_all_orders(id):
     async with async_session() as session:
         result = await session.scalars(select(Order).where(Order.id == id))
         return result