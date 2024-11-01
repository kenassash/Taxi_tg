import operator

from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Back,
    Button,
    Cancel,
    Column,
    Next,
    Row,
    ScrollingGroup,
    Select,
    Start,
    Group,
    SwitchTo,
    Multiselect
)
from aiogram_dialog.widgets.text import Const, Format, Multi
from app.dialog.callbacks import (
    start_order,
    on_choosen_city1,
    on_choosen_another_state,
    cancel_in_start,
    on_choosen_another1,
    back_in_start,
    on_choosen_adress1,
    on_choosen_city2,
    on_choosen_another_state2,
    on_choosen_another2,
    on_choosen_adress2,
    commit,
    order_now,
    upprice_order,
    cancel_upprice
)
from app.dialog.getters import (
    get_role_driver,
    get_role_user,
    get_city_inside1,
    getter_another_outside1,
    get_city_inside2,
    getter_another_outside2,
    get_order,
    get_upprice
)
from app.dialog.states import StartOrder, AddOrder

start_menu_order = Dialog(
    Window(
        Format('{text}'),
        Button(Const('Создать заказ 🏎️'),
               id='start_order',
               on_click=start_order),
        getter=get_role_driver,
        state=StartOrder.driver,
    ),
    Window(
        Format('{text}'),
        Button(Const('Создать заказ 🏎️'),
               id='start_order',
               on_click=start_order),
        getter=get_role_user,
        state=StartOrder.user,
    ),
)

# Определение диалога
start_menu_dialog = Dialog(
    Window(
        Const('<b>🅰️: Выберите откуда поедете:</b>'),
        Group(
            Select(
                Format('{item.city_name}'),
                id="city_from_input1",
                items="city_inside1",
                item_id_getter=operator.attrgetter('id'),
                on_click=on_choosen_city1,
            ),
            Button(
                Const(text="Другой населенный пункт"),
                id='another_locality1',
                on_click=on_choosen_another_state,
            ),
            id='city_from_input_ids1',
            width=2,
        ),
        Cancel(Const('Выйти'),
               id='cancel',
               on_click=cancel_in_start),
        getter=get_city_inside1,
        state=AddOrder.city1,
    ),
    Window(
        Const('🅰️: Выберите населенный пункт:'),
        ScrollingGroup(
            Select(
                text=Format("{item.city_name}"),
                id='another1_select',
                items='another_outside1',
                item_id_getter=operator.attrgetter('id'),
                on_click=on_choosen_another1,
            ),
            id='another_group1',
            height=14,
            width=2,
            hide_pager=False
        ),
        SwitchTo(Const('Назад'),
                 state=AddOrder.city1,
                 id='sw1',
                 on_click=back_in_start),
        getter=getter_another_outside1,
        state=AddOrder.another1,
    ),
    Window(
        Const('<b>🅰️: Напишите  Улицу и № дома\nНапример: Южная 8</b>'),
        TextInput(
            id='addres1_input',
            type_factory=str,
            on_success=on_choosen_adress1,
        ),
        SwitchTo(Const("Назад"),
                 id='sw2',
                 state=AddOrder.city1,
                 on_click=back_in_start),
        state=AddOrder.address1,
    ),
    Window(
        Format("<b>🅰️: {city1_id} - {address1_id}</b>\n"),
        Format("<b>🅱️: Выберите куда поедете:</b>"),

        Group(
            Select(
                Format('{item.city_name}'),
                id="city_from_input2",
                items="city_inside2",
                item_id_getter=operator.attrgetter('id'),
                on_click=on_choosen_city2,
            ),
            Button(Const(text="Другой населенный пункт"),
                   id='another_locality2',
                   on_click=on_choosen_another_state2),
            id='city_from_input_ids2',
            width=2,
        ),
        Back(Const("Назад")),
        Cancel(Const('Выйти'),
               id='cancel',
               on_click=cancel_in_start),
        getter=get_city_inside2,
        state=AddOrder.city2
    ),
    Window(
        Const('🅱️: Выберите населенный пункт:'),
        ScrollingGroup(
            Select(
                text=Format("{item.city_name}"),
                id='another2_select',
                items='another_outside2',
                item_id_getter=operator.attrgetter('id'),
                on_click=on_choosen_another2,
            ),
            id='another_group2',
            height=14,
            width=2,
            hide_pager=False
        ),
        SwitchTo(Const('Назад'),
                 state=AddOrder.city2,
                 id='sw3',
                 on_click=back_in_start),
        getter=getter_another_outside2,
        state=AddOrder.another2,
    ),
    Window(
        Const('<b>🅱️: Напишите  Улицу и № дома\nНапример: Южная 8</b>'),
        TextInput(
            id='addres2_input',
            type_factory=str,
            on_success=on_choosen_adress2,
        ),
        SwitchTo(Const("Назад"),
                 id='sw4',
                 state=AddOrder.city2),
        state=AddOrder.address2,
    ),
    Window(
        Format("🅰️ Начальная точка: <b>{city1_id} - {address1_id}</b>\n"),
        Format("🅱️ Конечная точка: <b>{city2_id} - {address2_id}</b>\n"),
        Format("➕ <b>{add_address}\n</b>", when='first_show'),
        Format("<b>Цена:</b> {price} руб"),
        Row(
            Multiselect(
                checked_text=Format('[🔘] {item[0]}'),
                unchecked_text=Format('[ ⚪️ ] {item[0]}'),
                id='multi_topics',
                item_id_getter=operator.itemgetter(1),
                items="topics",
                on_click=commit,
            ),
        ),
        Back(Const("Назад")),
        Cancel(Const('Выйти'),
               id='cancel',
               on_click=cancel_in_start),
        Button(Const('Заказать'),
               id='order',
               on_click=order_now),
        getter=get_order,
        state=AddOrder.order_start,
    ),
    Window(
        Const("<b>Ожидайте водителя⌛</b>\n"),
        Format("🅰️ Начальная точка: <b>{city1_id} - {address1_id}</b>\n"),
        Format("🅱️ Конечная точка: <b>{city2_id} - {address2_id}</b>\n"),
        Format("<b>Цена:</b> {price} руб"),
        Button(Const('⬆️ Ускорить на 20р'),
               id='upprice',
               on_click=upprice_order),
        Cancel(Const('Отменить'),
               id='cancel_price',
               on_click=cancel_upprice),
        getter=get_upprice,
        state=AddOrder.upprice,
    ),
)
