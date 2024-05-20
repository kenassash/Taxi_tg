from sqlalchemy.orm import joinedload, selectinload

from app.database.models import User, Order, Driver, OnlineExecution, Base, CityOutside, CityInside
from app.database.models import async_session

from sqlalchemy import select, update, delete, desc


async def set_user(tg_id, phone):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if not user:
            session.add(User(tg_id=tg_id, phone=phone))
            await session.commit()


async def get_users():
    async with async_session() as sesssion:
        users = await sesssion.scalars(select(User))
        return users


async def get_cities_inside():
    async with async_session() as sesssion:
        city = await sesssion.scalars(select(CityInside))
        return city


async def get_cities_outside():
    async with async_session() as sesssion:
        city = await sesssion.scalars(select(CityOutside))
        return city


async def set_order(user_id, data):
    async with async_session() as session:
        order = Order(**data)
        order.user = user_id
        session.add(order)
        await session.commit()  # Сохраняем изменения в базу данных
        await session.refresh(order)  # Обновляем объект, чтобы получить актуальный id
        return order.id


async def get_all_orders(id):
    async with async_session() as session:
        # result = await session.scalar(select(Order).where(Order.id == id))
        result = await session.scalar(select(Order)
                                      .where(Order.id == id)
                                      .options(joinedload(Order.user_rel)))
        return result


async def add_car(data):
    async with async_session() as session:
        driver = Driver(**data)
        session.add(driver)
        await session.commit()
        await session.refresh(driver)  # Обновляем объект, чтобы получить актуальный id
        return driver.id


async def get_driver(tg_id):
    async with async_session() as session:
        driver = await session.scalar(select(Driver).where(Driver.tg_id == tg_id))
        return driver


async def get_user(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user


async def active_driver(tg_id, is_start=True):
    async with async_session() as session:
        driver = await session.scalar(select(Driver).where(Driver.tg_id == tg_id))
        driver.active = is_start
        await session.commit()


async def get_all_car():
    async with async_session() as session:
        driver = await session.scalars(select(Driver))
        return driver


async def get_one_car(id):
    async with async_session() as session:
        driver = await session.scalar(select(Driver).where(Driver.id == id))
        return driver


async def remove_car(id):
    async with async_session() as session:
        await session.execute(delete(Driver).where(Driver.id == id))
        await session.commit()


async def start_order_execution(order_id_id, driver_id_id):
    async with async_session() as session:
        # --------Создаем запись о начале выполнения заказа в OnlineExecution
        order_execution = OnlineExecution(order_id=order_id_id, driver_id=driver_id_id)
        session.add(order_execution)
        await session.commit()


async def delete_order_execution(order_id_id, driver_id_id):
    async with async_session() as session:
        # ---------- удаляем запись о начале выполнения заказа в OnlineExecution
        await session.execute(
            delete(OnlineExecution)
            .where(
                (OnlineExecution.order_id == order_id_id) &
                (OnlineExecution.driver_id == driver_id_id)
            )
        )
        await session.commit()


async def delete_order_pass(order_id_id):
    async with async_session() as session:
        # ---------- удаляем запись о начале выполнения заказа в OnlineExecution
        await session.execute(
            delete(OnlineExecution)
            .where(
                (OnlineExecution.order_id == order_id_id)

            )
        )
        await session.execute(delete(Order).where(Order.id == order_id_id))
        await session.commit()


async def reset_to_zero(driver_id_id):
    async with async_session() as session:
        # ---------- обнуляем об водителе в  OnlineExecution
        await session.execute(
            delete(OnlineExecution)
            .where(
                (OnlineExecution.driver_id == driver_id_id)
            )
        )
        await session.commit()


async def print_all_online_executions():
    async with async_session() as session:
        # ------ Выполняем запрос для получения всех онлайн-исполнений-----------------
        query = (
            select(Driver)
            .options(selectinload(Driver.orders_reply))
        )
        res = await session.execute(query)
        result = res.unique().scalars().all()
        return result


async def get_all_drivers_with_update_date():
    async with async_session() as session:
        # Выполняем запрос на получение всех водителей с их датой обновления,
        # с сортировкой по статусу активности и дате обновления
        drivers_query = select(Driver).order_by(Driver.active.desc(), desc(Driver.updated))
        result = await session.execute(drivers_query)
        drivers = result.scalars().all()
        return drivers


async def get_driver_info(driver_id: int) -> dict:
    async with async_session() as session:
        # Получаем информацию о водителе
        query_driver = (
            select(Driver)
            .options(
                selectinload(Driver.orders_reply)
            )
            .where(Driver.id == driver_id)
        )
        result_driver = await session.execute(query_driver)
        driver = result_driver.unique().scalars().first()
        return driver


async def get_order_driver(order_id):
    async with async_session() as session:
        # Получаем информацию о водителе
        query_driver = (
            select(Order)
            .options(
                selectinload(Order.drivers_reply)  # Загрузка связанных водителей
            )
            .where(Order.id == order_id)
        )
        result_driver = await session.execute(query_driver)
        order = result_driver.scalar()
        if order and order.drivers_reply:
            driver = order.drivers_reply[0]  # Предполагаем, что выбираем первого водителя из списка
            return driver
        return None
