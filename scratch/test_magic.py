from aiogram import F
from src.bot.keyboards.user_menu import USER_MENU_ALIASES
ALL_MENU_ALIASES = [alias for aliases in USER_MENU_ALIASES.values() for alias in aliases]

class Dummy:
    def __init__(self, text):
        self.text = text

msg = Dummy("\U0001F393 Ta'lim")
print("Matches?", F.text.in_(ALL_MENU_ALIASES).resolve(msg))
