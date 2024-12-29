from sqlalchemy.orm import joinedload, selectinload

from app.database.models import User, Order, Driver, OnlineExecution, Base, CityOutside, CityInside, CityRoutes
from app.database.models import async_session

from sqlalchemy import select, update, delete, desc, or_


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


async def get_order(order_id):
    async with async_session() as sesssion:
        order = await sesssion.scalar(select(Order).where(Order.id == order_id))
        return order


async def get_cities_inside_test(id):
    id = int(id)
    async with async_session() as sesssion:
        city1 = await sesssion.scalar(select(CityInside).where(CityInside.id == id))
        return city1


async def get_cities_inside():
    async with async_session() as sesssion:
        city = await sesssion.scalars(select(CityInside))
        return city


async def get_cities_outside():
    async with async_session() as sesssion:
        city = await sesssion.scalars(select(CityOutside))
        return city


async def get_cities_inside_id(id):
    id = int(id)
    async with async_session() as sesssion:
        city1 = await sesssion.scalar(select(CityOutside).where(CityOutside.id == id))
        return city1
async def get_cities_outside_name(name):
    async with async_session() as sesssion:
        city_name = await sesssion.scalar(select(CityOutside).where(CityOutside.city_name == name))
        return city_name

async def get_cities_routes1():
    async with async_session() as session:
        query = select(CityRoutes.city1).distinct()
        result = await session.execute(query)
        unique_routes = result.fetchall()
        return unique_routes


async def get_cities_routes2(city1: str):
    async with async_session() as session:
        city2 = await session.scalars(select(CityRoutes.city2).where(CityRoutes.city1 == city1))
        return city2


async def get_cities_routes_price(city1: str, city2: str):
    async with async_session() as session:
        price = await session.scalar(
            select(CityRoutes.price)
            .where((CityRoutes.city1 == city1) & (CityRoutes.city2 == city2))
        )
        return price


async def get_cities_routes_price_update(city1: str, city2: str, price: int):
    price = int(price)
    async with async_session() as session:
        price = (
            update(CityRoutes)
            .where((CityRoutes.city1 == city1) & (CityRoutes.city2 == city2))
            .values(price=price)
            .execution_options(synchronize_session="fetch")
        )
        await session.execute(price)
        await session.commit()

async def city_routers_update_all(price_delta: str):
    price_delta = int(price_delta)
    async with async_session() as session:
        price = (
            update(CityRoutes)
            .values(price=CityRoutes.price + price_delta)
            .execution_options(synchronize_session="fetch")
        )
        await session.execute(price)
        await session.commit()
async def set_order(user_id, data):
    user_id = int(user_id)
    async with async_session() as session:
        order = Order(**data)
        order.user = user_id
        session.add(order)
        await session.commit()  # Сохраняем изменения в базу данных
        await session.refresh(order)  # Обновляем объект, чтобы получить актуальный id
        return order.id



async def shop_order_add(user_id, price):
    async with async_session() as session:
        order = Order(user=user_id, price=price)
        session.add(order)
        await session.commit()  # Сохраняем изменения в базу данных
        await session.refresh(order)  # Обновляем объект, чтобы получить актуальный id
        return order.id


async def save_free_ride(tg_id, free_ride):
    async with async_session() as session:
        await session.execute(update(User)
                              .where(User.tg_id == tg_id)
                              .values(free_ride=free_ride))
        await session.commit()

async def save_free_ride_by_phone(phone, free_ride):
    async with (async_session() as session):
        result = await session.execute(update(User)
                              .where(User.phone == phone)
                              .values(free_ride=free_ride)
                              .returning(User.tg_id))
        await session.commit()
        tg_id = result.scalar()  # scalar() возвращает одну строку
        return tg_id
async def get_all_orders(id):
    id = int(id)
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


async def no_active(driver_id, is_start=False):
    async with async_session() as session:
        driver = await session.scalar(select(Driver).where(Driver.id == driver_id))
        driver.active = is_start
        await session.commit()


async def get_all_car():
    async with async_session() as session:
        driver = await session.scalars(select(Driver))
        return driver


async def get_one_car(id):
    id = int(id)
    async with async_session() as session:
        driver = await session.scalar(select(Driver).where(Driver.id == id))
        return driver


async def update_car(data):
    async with async_session() as session:
        driver_id = data.pop('driver_id')  # Извлекаем driver_id и удаляем его из словаря
        query = (
            update(Driver)
            .where(Driver.id == driver_id)
            .values(**data)
            .execution_options(synchronize_session="fetch")
        )
        await session.execute(query)
        await session.commit()


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
    order_id_id = int(order_id_id)
    async with async_session() as session:
        # ---------- удаляем запись о начале выполнения заказа в OnlineExecution
        await session.execute(
            delete(OnlineExecution)
            .where(
                (OnlineExecution.order_id == order_id_id)

            )
        )
        # await session.execute(delete(Order).where(Order.id == order_id_id))
        await session.commit()


async def reset_to_zero(driver_id_id):
    driver_id_id = int(driver_id_id)
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
    order_id = int(order_id)
    async with async_session() as session:
        # Получаем информацию о водителе
        query_driver = (
            select(Order)
            .options(
                selectinload(Order.drivers_reply),
                selectinload(Order.user_rel)# Загрузка связанных водителей

            )
            .where(Order.id == order_id)
        )
        result_driver = await session.execute(query_driver)
        order = result_driver.scalar()
        if order:
            return order
        return None


async def up_price_passager(order_id, price_passager):
    async with async_session() as session:
        await session.execute(update(Order)
                              .where(Order.id == order_id)
                              .values(price=Order.price + price_passager)
                              )
        await session.commit()
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.user_rel))
            .where(Order.id == order_id)
        )
        order_instance = result.scalar_one_or_none()
        await session.refresh(order_instance)
        return order_instance

async def set_chat_id_user(order_id, chat_id_driverid):
    chat_id_driverid = str(chat_id_driverid)
    async with async_session() as session:
        query = update(Order).where(Order.id == order_id).values(chat_id_driver=chat_id_driverid)
        await session.execute(query)
        await session.commit()

async def set_chat_id_driver(order_id, chat_id_userid):
    chat_id_userid = str(chat_id_userid)
    async with async_session() as session:
        query = update(Order).where(Order.id == order_id).values(chat_id_user=chat_id_userid)
        await session.execute(query)
        await session.commit()
async def get_users_count():
    async with async_session() as session:
        stmt = select(User)
        result = await session.execute(stmt)
        count = len(result.all())
        return count


async def update_price_count():
    async with async_session() as session:
        stmt = select(User)
        result = await session.execute(stmt)
        count = len(result.all())
        return count


async def add_change_price(price, city, database):
    async with async_session() as session:
        if database == "inside":
            # Обновляем цену в таблице CityInside
            query = update(CityInside).where(CityInside.city_name == city).values(price=price)
        elif database == "outside":
            # Обновляем цену в таблице CityOutside
            query = update(CityOutside).where(CityOutside.city_name == city).values(price=price)
        else:
            # Обработка других случаев
            pass

        # Выполняем запрос
        await session.execute(query)

        # Сохраняем изменения в базе данных
        await session.commit()


async def ban_user(phone, banned_id):
    async with async_session() as session:
        # Обновляем поле "banned" для пользователя с заданным tg_id
        await session.execute(update(User).where(User.phone == phone).values(banned=banned_id))
        await session.commit()


async def get_ban_all_user():
    async with async_session() as session:
        # Обновляем поле "banned" для пользователя с заданным tg_id
        ban_active = True
        ban_user = await session.scalars(select(User).where(User.banned == ban_active))
        return ban_user


async def check_user_banned(user_id):
    async with async_session() as session:
        # Выполняем запрос к базе данных для получения статуса блокировки пользователя
        user = await session.execute(select(User.banned).filter_by(tg_id=user_id))
        user_banned = user.scalar()

    return user_banned


async def shop_check(user_id):
    async with async_session() as session:
        # Выполняем запрос к базе данных для получения статуса магазина
        user = await session.execute(select(User.shop_activate).filter_by(tg_id=user_id))
        shop_user = user.scalar()

    return shop_user


async def shop_add(user_id, shop_name, shop_activate=True):
    async with async_session() as session:
        # Добавляем магазин
        await session.execute(update(User)
                              .where(User.tg_id == user_id)
                              .values(shop_activate=shop_activate,
                                      shop_name=shop_name))
        await session.commit()


async def get_route_price(city1: str, city2: str):
    async with async_session() as session:
        route = select(CityRoutes).where(
            ((CityRoutes.city1 == city1) & (CityRoutes.city2 == city2)) |
            ((CityRoutes.city1 == city2) & (CityRoutes.city2 == city1))
        )
        result = await session.execute(route)
        route = result.scalar_one_or_none()
        return route.price if route else None
