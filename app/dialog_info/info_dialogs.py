from operator import itemgetter

from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import  NumberedPager
from aiogram_dialog.widgets.text import Format, Const, List

from app.database.requests import get_cities_outside

class Information(StatesGroup):
    info_np = State()

async def infoname_getter(dialog_manager: DialogManager, **kwargs):
    another_outside2 = await get_cities_outside()
    data = {
        'info': sorted(
            [
                (f"{city.city_name} - {city.price}₽", city.id)  # тут имя + цена
                for city in another_outside2
            ],
            key=lambda x: x[0]  # сортируем по имени+цене
        ),
    }
    return data

info_menu = Dialog(
    Window(
        Const('🗺️ Информация по другому населенному пункту\n'),
        List(
            Format("{pos}. {item[0]}"),
            items="info",
            id="list_scroll",
            page_size=20,
        ),
        NumberedPager(
            scroll="list_scroll",
        ),
        getter=infoname_getter,
        preview_data=infoname_getter,
        state=Information.info_np,
    )
)
