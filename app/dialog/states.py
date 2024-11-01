from aiogram.fsm.state import StatesGroup, State


class StartOrder(StatesGroup):
    driver = State()
    user = State()
    request_phone = State()


class AddOrder(StatesGroup):
    city1 = State()
    address1 = State()
    another1 = State()

    city2 = State()
    address2 = State()
    another2 = State()

    order_start = State()
    upprice = State()

class AddUser(StatesGroup):
    phone = State()
