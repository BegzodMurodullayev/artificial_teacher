from src.bot.handlers.admin.dashboard import _extract_broadcast_text
from src.bot.keyboards.user_menu import resolve_menu_action


def test_admin_stat_button_maps_to_admin_stats_action():
    assert resolve_menu_action("\U0001f4c8 Statistika") == "adm_stats"
    assert resolve_menu_action("\U0001f4ca Statistika") == "stats"


def test_broadcast_text_extraction_supports_plain_and_mention_commands():
    assert _extract_broadcast_text("/broadcast Salom") == "Salom"
    assert _extract_broadcast_text("/broadcast@Artificial_teacher_bot Salom") == "Salom"
    assert _extract_broadcast_text("/broadcast") == ""
    assert _extract_broadcast_text("/other test") == ""
