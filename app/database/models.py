import os
from typing import List

from sqlalchemy import BigInteger, ForeignKey, String, DateTime, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

from dotenv import load_dotenv

load_dotenv()
engine = create_async_engine(url=os.getenv('ENGINE'), echo=True)

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


"""
Пассажиры(ид, телефон, тег_ид)
Водители(ид, телефон, фирма машины, номер машины,Координаты, фото машины, тег_ид)
Заказ(ид, телефон, начальная точка, конечная точка, цена, тег_ид
"""


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)
    phone: Mapped[int] = mapped_column(nullable=True)

    order_rel: Mapped[List['Order']] = relationship(back_populates='user_rel')


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)

    user: Mapped[int] = mapped_column(ForeignKey('users.id'))


    point_start: Mapped[str] = mapped_column(String(200))
    point_end: Mapped[str] = mapped_column(String(200))

    distance: Mapped[int] = mapped_column(nullable=True)
    time_way: Mapped[int] = mapped_column(nullable=True)
    price: Mapped[int] = mapped_column(nullable=True)

    coordinat_start_x: Mapped[float] = mapped_column(nullable=True)
    coordinat_start_y: Mapped[float] = mapped_column(nullable=True)
    coordinat_end_x: Mapped[float] = mapped_column(nullable=True)
    coordinat_end_y: Mapped[float] = mapped_column(nullable=True)

    drivers_reply: Mapped[List['Driver']] = relationship(back_populates='orders_reply',
                                                         secondary='order_executions')
    user_rel: Mapped['User'] = relationship(back_populates='order_rel')


class Driver(Base):
    __tablename__ = 'drivers'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)
    phone: Mapped[int] = mapped_column(nullable=True)
    car_name: Mapped[str] = mapped_column(String(100))
    number_car: Mapped[int] = mapped_column(nullable=True)
    photo_car: Mapped[str] = mapped_column(String(150), nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=False)

    orders_reply: Mapped[List['Order']] = relationship(back_populates='drivers_reply',
                                                       secondary='order_executions')


class OnlineExecution(Base):
    __tablename__ = 'order_executions'

    driver_id: Mapped[int] = mapped_column(ForeignKey('drivers.id', ondelete='CASCADE'), primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id', ondelete='CASCADE'), primary_key=True)


async def async_main():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

