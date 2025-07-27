from dataclasses import dataclass

from aiogram.fsm.state import State, StatesGroup
from typing import List


@dataclass
class Template:
    category: str
    subcategory: str
    button_text: str
    keywords: List[str]
    answer_ukr: str
    answer_rus: str
    sort_order: int
    has_menu_button: bool = True  # По умолчанию True для обновления существующих шаблонов


class UserStates(StatesGroup):
    main_menu = State()
    category_menu = State()
    search_mode = State()
    ai_mode = State()
    admin_correction = State()
    admin_addition = State()
