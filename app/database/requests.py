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


async def get_order(order_id):
    async with async_session() as sesssion:
        order = await sesssion.scalar(select(Order).where(Order.id == order_id))
        return order


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
                selectinload(Order.drivers_reply),  # Загрузка связанных водителей

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

# locations = {
#     "Анновка": 2700,
#     "Архара": 5800,
#     "Аэропорт": 5500,
#     "Борисоглебка": 1800,
#     "Благовещенск": 4800,
#     "Белогорск": 3500,
#     "Беляковка": 1900,
#     "Березовка": 4300,
#     "Верхнебелое": 1400,
#     "Владимировка": 4500,
#     "Вознесеновка": 2300,
#     "Высокое": 1500,
#     "Возжаевка": 2300,
#     "Варваровка": 1800,
#     "Георгиевка": 800,  # исправлено с 1400
#     "Долдыкан": 3200,
#     "Дальневосточное": 1300,
#     "Зорино": 800,
#     "Завитинск": 1600,
#     "Знаменка": 1500,
#     "Серышево": 4200,
#     "Трудовой": 1900,
#     "Талакан": 4200,
#     "Тамбовка": 3200,
#     "Ивановка": 3500,
#     "Ильиновка": 2300,
#     "Короли (федералка)": 850,
#     "Короли": 700,
#     "Козьмодемьяновка": 2000,
#     "Каховка": 2350,
#     "Кутилово": 1400,
#     "Климовка": 2300,
#     "Любимое": 1800,
#     "Максимовка": 1200,
#     "МПС (нефть)": 750,
#     "Мухинский": 1300,
#     "Марьяновка": 1100,
#     "Морозова": 2000,
#     "Николо-Александровка": 1700,
#     "Нагорный": 400,
#     "Новомихайловка": 850,
#     "Заречное (Белогорский р-он)": 2600,
#     "Преображеновка": 1400,
#     "Прогресс": 4200,
#     "Песчаноозёрка": 1400,
#     "Поярково": 4200,
#     "Поздеевка (федералка)": 1800,
#     "Переяславка": 1000,
#     "Прибрежный": 450,
#     "Покровка": 1500,
#     "Панино": 250,
#     "Романовка": 750,
#     "Ромны": 2000,
#     "Райчихинск": 3500,
#     "Рогозовка": 1700,
#     "Смелое": 1200,
#     "Среднебелая": 4500,
#     "Сергеев-Фёдоровка": 1000,
#     "Свободный": 6000,
#     "Смирновка (федералка)": 1200,
#     "Святорусовка": 1200,
#     "Солнечное": 4500,  # исправлено с 4000
#     "Новоросийка": 1800,
#     "Новобурейский": 3500,
#     "Новокиевский Увал": 6500,
#     "Урожайное": 750,
#     "Чигири": 4800,
#     "Черёмушки": 1200,
#     "Шимановск": 8600,
#     "Харьковка": 140,  # исправлено
#     "Южное": 200,  # исправлено с 400
#     "Ерковцы": 2200,
#     "Ясная Поляна": 1600
# }

# cities = {
#     "Екатеринославка": 150,
#     "Таёжный": 200,
#     "Полигон": 350,
#     "Восточный за ж/д": 200,
#     "Агрохолдинг": 300,
# }
# async def test_driver():
#     async with async_session() as session:
#         for city, price in cities.items():
#             session.add(CityInside(city_name=city, price=price))
#         await session.commit()
