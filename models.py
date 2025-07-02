from dataclasses import dataclass
from typing import List

from aiogram.fsm.state import State, StatesGroup


@dataclass
class Template:
    category: str
    subcategory: str
    button_text: str
    keywords: List[str]
    answer_ukr: str
    answer_rus: str
    sort_order: int


class UserStates(StatesGroup):
    main_menu = State()
    category_menu = State()
    search_mode = State()
