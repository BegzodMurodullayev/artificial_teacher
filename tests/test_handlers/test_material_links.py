from src.bot.keyboards import user_menu


def test_material_links_are_resolved_separately_from_main_webapp():
    original = {
        "WEB_APP_URL": user_menu.settings.WEB_APP_URL,
        "WEB_APP_URL_PRO": user_menu.settings.WEB_APP_URL_PRO,
        "MATERIALS_URL": user_menu.settings.MATERIALS_URL,
        "MATERIALS_URL_PRO": user_menu.settings.MATERIALS_URL_PRO,
    }
    try:
        user_menu.settings.WEB_APP_URL = "https://app.example"
        user_menu.settings.WEB_APP_URL_PRO = "https://pro-app.example"
        user_menu.settings.MATERIALS_URL = ""
        user_menu.settings.MATERIALS_URL_PRO = "https://pro-materials.example"

        url, resolved_plan = user_menu.resolve_materials_launch("pro")

        assert user_menu.resolve_webapp_url("pro") == "https://pro-app.example"
        assert url == "https://pro-materials.example"
        assert resolved_plan == "pro"
    finally:
        for key, value in original.items():
            setattr(user_menu.settings, key, value)


def test_material_links_fall_back_to_lower_available_tier():
    original = {
        "MATERIALS_URL": user_menu.settings.MATERIALS_URL,
        "MATERIALS_URL_FREE": user_menu.settings.MATERIALS_URL_FREE,
        "MATERIALS_URL_STANDARD": user_menu.settings.MATERIALS_URL_STANDARD,
        "MATERIALS_URL_PRO": user_menu.settings.MATERIALS_URL_PRO,
    }
    try:
        user_menu.settings.MATERIALS_URL = ""
        user_menu.settings.MATERIALS_URL_FREE = "https://free-materials.example"
        user_menu.settings.MATERIALS_URL_STANDARD = "https://standard-materials.example"
        user_menu.settings.MATERIALS_URL_PRO = ""

        url, resolved_plan = user_menu.resolve_materials_launch("pro")

        assert url == "https://standard-materials.example"
        assert resolved_plan == "standard"
    finally:
        for key, value in original.items():
            setattr(user_menu.settings, key, value)
