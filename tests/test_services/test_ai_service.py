import json
from pathlib import Path

from src.services.ai_service import _normalize_mode


def test_translate_mode_aliases_are_supported():
    assert _normalize_mode("translate_uz_to_en") == "translate_uz_en"
    assert _normalize_mode("translate_en_to_uz") == "translate_en_uz"
    assert _normalize_mode("translate_ru_to_en") == "translate_ru_en"
    assert _normalize_mode("translate_en_to_ru") == "translate_en_ru"


def test_material_seed_file_has_supported_types():
    seed_path = Path("src/data/materials_seed.json")
    payload = json.loads(seed_path.read_text(encoding="utf-8"))

    assert payload, "materials seed should not be empty"
    assert {"book", "fact", "quiz", "guide"} <= {item["material_type"] for item in payload}
    assert all(isinstance(item.get("content"), dict) for item in payload)
    assert all(item["content"].get("tier") in {"free", "standard", "pro", "premium"} for item in payload)
