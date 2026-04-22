import sys
from src.bot.keyboards.user_menu import USER_MENU_ALIASES
ALL_MENU_ALIASES = [alias for aliases in USER_MENU_ALIASES.values() for alias in aliases]
print("All aliases:", ALL_MENU_ALIASES)
print("Contains '🎓 Ta\\'lim':", "🎓 Ta'lim" in ALL_MENU_ALIASES)
