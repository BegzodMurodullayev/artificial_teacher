from src.bot.handlers.user.legacy_callbacks import resolve_legacy_callback_action
from src.bot.keyboards.user_menu import resolve_menu_action
from src.bot.middlewares.sponsor import should_bypass_sponsor_callback


def test_plain_menu_aliases_map_to_main_menu():
    assert resolve_menu_action("Menu") == "main_menu"
    assert resolve_menu_action("menyu") == "main_menu"
    assert resolve_menu_action("Bosh menyu") == "main_menu"


def test_legacy_callback_mapping_covers_old_inline_payloads():
    assert resolve_legacy_callback_action("menu_back") == "main_menu"
    assert resolve_legacy_callback_action("trdir__uz_to_en") == "translate_direction"
    assert resolve_legacy_callback_action("lesson__custom") == "lesson_topic"
    assert resolve_legacy_callback_action("qpick_quiz_10") == "restart_quiz"
    assert resolve_legacy_callback_action("unknown_payload") is None


def test_sponsor_recheck_callbacks_bypass_sponsor_block():
    assert should_bypass_sponsor_callback("check_sponsor") is True
    assert should_bypass_sponsor_callback("sponsor_recheck") is True
    assert should_bypass_sponsor_callback("menu_back") is False
