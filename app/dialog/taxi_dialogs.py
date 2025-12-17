import operator
from operator import itemgetter

from aiogram import F
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
    Multiselect, PrevPage, NextPage, Radio
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
    cancel_upprice, add_new_address_cb, on_choosen_add_address_cb, order_now_with_new_address1,
    add_new_address1, add_new_address2, add_new_address_cb2, on_choosen_add_address_cb2, order_now_with_new_address2,
    get_info_by_driver_handler, on_paid_free_selected, on_driver_status_changed
)
from app.dialog.getters import (
    get_role_driver,
    get_role_user,
    get_city_inside1,
    getter_another_outside1,
    get_city_inside2,
    getter_another_outside2,
    get_order,
    get_upprice, add_new_address_getter, get_order_with_new_address1, add_new_address_getter2,
    get_order_with_new_address2
)
from app.dialog.states import StartOrder, AddOrder

start_menu_order = Dialog(
    Window(
        Format('{text}'),
        Button(Const('🚕СОЗДАТЬ ЗАКАЗ🚕'),
               id='start_order',
               on_click=start_order,
               when=((~F["paid_free"]) | F["paid_free_selected"])
               ),
        Radio(
            Format("✓ {item[0]}"),
            Format("  {item[0]}"),
            id="free_id",
            item_id_getter=operator.itemgetter(1),
            items="paid_free_items",
            when=F["paid_free"],
            on_state_changed=on_paid_free_selected,
        ),
        Radio(
            Format("✓ {item[0]}"),
            Format("  {item[0]}"),
            id="driver_status_id",
            item_id_getter=operator.itemgetter(1),
            items="driver_status_items",
            when=(F["is_driver"] & F["show_driver_status"]),  # Показываем только водителям и когда авто-распределение включено
            on_state_changed=on_driver_status_changed,  # Нужно создать эту функцию
        ),
        Button(
            text=Const("Аккаунт"),
            id="button_get_about_driver",
            on_click=get_info_by_driver_handler,
            when=F["is_driver"]
        ),
        getter=get_role_driver,
        state=StartOrder.user,
    ),
)

# Определение диалога
start_menu_dialog = Dialog(
    Window(
        Const('<b>📍: Выберите откуда поедете:</b>'),
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
                when='allow_another',
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
        Const('📍: Выберите населенный пункт:'),
        ScrollingGroup(
            Select(
                text=Format("{item[0]}"),
                id='another1_select',
                items='another_outside1',
                item_id_getter=itemgetter(1),
                on_click=on_choosen_another1,
            ),
            id='another_group1',
            height=14,
            width=2,
            hide_pager=True
        ),
        Row(
            PrevPage(
                scroll='another_group1', text=Format("◀️"),
            ),
            NextPage(
                scroll='another_group1', text=Format("▶️"),
            ),
        ),
        SwitchTo(Const('Назад'),
                 state=AddOrder.city1,
                 id='sw1',
                 on_click=back_in_start),
        getter=getter_another_outside1,
        state=AddOrder.another1,
    ),
    Window(
        Const('<b>Напишите  улицу и № дома откуда поедите\nНапример: Южная 8</b>'),
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
        Format("<b>📍: {city1_id} - {address1_id}</b>\n"),
        Format("<b>📍: Выберите куда поедете:</b>"),

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
                   on_click=on_choosen_another_state2,
                   when='allow_another'),
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
        Const('📍: Выберите населенный пункт:'),
        ScrollingGroup(
            Select(
                text=Format("{item[0]}"),
                id='another2_select',
                items='another_outside2',
                item_id_getter=itemgetter(1),
                on_click=on_choosen_another2,
            ),
            id='another_group2',
            height=14,
            width=2,
            hide_pager=True
        ),
        Row(
            PrevPage(
                scroll='another_group2', text=Format("◀️"),
            ),
            NextPage(
                scroll='another_group2', text=Format("▶️"),
            ),
        ),
        SwitchTo(Const('Назад'),
                 state=AddOrder.city2,
                 id='sw3',
                 on_click=back_in_start),
        getter=getter_another_outside2,
        state=AddOrder.another2,
    ),
    Window(
        Const('<b>Напишите  улицу и № дома куда поедите\nНапример: Ленина 16</b>'),
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
        Format("📍 Начальная точка: <b>{city1_id} - {address1_id}</b>\n"),
        Format("📍 Конечная точка: <b>{city2_id} - {address2_id}</b>\n"),
        Format("🔃 <b>{topics[0][0]}\n</b>", when='first_show'),
        Format("<b>Цена:</b> {price} руб"),
        Row(
            Multiselect(
                checked_text=Format('{item[0]}'),
                unchecked_text=Format('🔃 {item[0]}'),
                id='multi_topics',
                item_id_getter=operator.itemgetter(1),
                items="topics",
                # on_click=commit, # если on_click приходится 2 раза нажимать
                on_state_changed=commit,  # с первого раза элемент
            ),
        ),
        Button(Const('Добавить адрес'),
               id='add_address1',
               on_click=add_new_address1,
               when='another_hide'),
        Back(Const("Назад")),
        Cancel(Const('Выйти'),
               id='cancel',
               on_click=cancel_in_start),
        Button(Const('ЗАКАЗАТЬ'),
               id='order',
               on_click=order_now),
        getter=get_order,
        state=AddOrder.order_start,
    ),
    Window(
        Const('📍: Выберите дополнительный адрес'),
        Group(
            Select(
                Format('{item.city_name}'),
                id="add_new_address_id",
                items="new_address1",
                item_id_getter=operator.attrgetter('id'),
                on_click=add_new_address_cb,
            ),
            id='add_new_address_ids',
            width=2,
        ),
        Back(Const("Назад")),
        Cancel(Const('Выйти'),
               id='cancel',
               on_click=cancel_in_start),
        getter=add_new_address_getter,
        state=AddOrder.add_new_address1
    ),
    Window(
        Const('<b>Напишите  улицу и № дома куда поедите\nНапример: Северная 12</b>'),
        TextInput(
            id='add_street_address1',
            type_factory=str,
            on_success=on_choosen_add_address_cb,
        ),
        SwitchTo(Const("Назад"),
                 id='sw5',
                 state=AddOrder.order_start),
        state=AddOrder.add_street_address1
    ),
    Window(
        Format("📍: <b>{city1_id} - {address1_id}</b>\n"),
        Format("📍: <b>{city2_id} - {address2_id}</b>\n"),
        Format("📍: <b>{add_new_address1} - {add_street_address1}</b>\n"),
        Format("<b>Цена:</b> {price} руб"),
        Button(Const('Добавить адрес'),
               id='add_address2',
               on_click=add_new_address2,
               when='another_hide'),
        SwitchTo(Const("Назад"),
                 id='sw6',
                 state=AddOrder.order_start),
        Cancel(Const('Выйти'),
               id='cancel',
               on_click=cancel_in_start),
        Button(Const('ЗАКАЗАТЬ'),
               id='order_with_na1',
               on_click=order_now_with_new_address1),
        getter=get_order_with_new_address1,
        state=AddOrder.order_start_with_new_address1,
    ),
    Window(
        Const('📍: Выберите дополнительный адрес'),
        Group(
            Select(
                Format('{item.city_name}'),
                id="add_new_address_id2",
                items="new_address2",
                item_id_getter=operator.attrgetter('id'),
                on_click=add_new_address_cb2,
            ),
            id='add_new_address_ids2',
            width=2,
        ),
        SwitchTo(Const("Назад"),
                 id='sw6',
                 state=AddOrder.order_start),
        Cancel(Const('Выйти'),
               id='cancel',
               on_click=cancel_in_start),
        getter=add_new_address_getter2,
        state=AddOrder.add_new_address2
    ),
    Window(
        Const('<b>Напишите  улицу и № дома куда поедите\nНапример: Горького 12</b>'),
        TextInput(
            id='add_street_address2',
            type_factory=str,
            on_success=on_choosen_add_address_cb2,
        ),
        SwitchTo(Const("Назад"),
                 id='sw6',
                 state=AddOrder.order_start),
        state=AddOrder.add_street_address2
    ),
    Window(
        Format("📍: <b>{city1_id} - {address1_id}</b>\n"),
        Format("📍: <b>{city2_id} - {address2_id}</b>\n"),
        Format("📍: <b>{add_new_address1} - {add_street_address1}</b>\n"),
        Format("📍: <b>{add_new_address2} - {add_street_address2}</b>\n"),
        Format("<b>Цена:</b> {price} руб"),
        SwitchTo(Const("Назад"),
                 id='sw6',
                 state=AddOrder.order_start),
        Cancel(Const('Выйти'),
               id='cancel',
               on_click=cancel_in_start),
        Button(Const('ЗАКАЗАТЬ'),
               id='order_with_na1',
               on_click=order_now_with_new_address2),
        getter=get_order_with_new_address2,
        state=AddOrder.order_start_with_new_address2,
    ),
    Window(
        Const("<b>Ожидайте водителя⌛</b>\n"),
        Format("📍: <b>{city1_id} - {address1_id}</b>\n"),
        Format("📍: <b>{city2_id} - {address2_id}</b>\n"),
        Format("📍: <b>{add_new_address1} - {add_street_address1}</b>\n",
               when='getter_new_address1'),
        Format("📍: <b>{add_new_address2} - {add_street_address2}</b>\n",
               when='getter_new_address2'),
        Format("🔃 <b>{add_address}\n</b>", when='first_show'),
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
