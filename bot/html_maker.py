"""HTML document renderer for Telegram exports."""
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    enable_async=False,
)

_BASE_THEMES = {
    "atlas": {"bg_a": "#f8efe3", "bg_b": "#eadcc6", "paper": "#fffaf4", "paper_alt": "#fff2e1", "ink": "#1f2937", "muted": "#6b7280", "accent": "#b55d2f", "accent_2": "#f59e0b", "line": "#ead7c0", "good": "#166534", "bad": "#b91c1c"},
    "emerald": {"bg_a": "#edf8f1", "bg_b": "#d8f0e4", "paper": "#fbfffc", "paper_alt": "#effbf4", "ink": "#193126", "muted": "#4c6b5c", "accent": "#14825f", "accent_2": "#55c08d", "line": "#c9e8d8", "good": "#166534", "bad": "#b91c1c"},
    "ocean": {"bg_a": "#eaf4fb", "bg_b": "#d8ebf9", "paper": "#fbfdff", "paper_alt": "#eef7ff", "ink": "#172533", "muted": "#4f6b80", "accent": "#1f6eb3", "accent_2": "#60a5fa", "line": "#cbdff2", "good": "#0f766e", "bad": "#b91c1c"},
    "rose": {"bg_a": "#fff1f3", "bg_b": "#ffe0e6", "paper": "#fffafb", "paper_alt": "#fff0f4", "ink": "#341b27", "muted": "#7f5868", "accent": "#c2416c", "accent_2": "#fb7185", "line": "#f3d0da", "good": "#166534", "bad": "#b91c1c"},
    "midnight": {"bg_a": "#0f172a", "bg_b": "#172033", "paper": "#111827", "paper_alt": "#172136", "ink": "#e5eef8", "muted": "#93a4bb", "accent": "#38bdf8", "accent_2": "#a78bfa", "line": "#243247", "good": "#22c55e", "bad": "#fb7185"},
    "saffron": {"bg_a": "#fff6df", "bg_b": "#f6e6b7", "paper": "#fffdf5", "paper_alt": "#fff5d8", "ink": "#3a2d17", "muted": "#746043", "accent": "#ca8a04", "accent_2": "#f59e0b", "line": "#ecdca9", "good": "#15803d", "bad": "#b91c1c"},
    "graphite": {"bg_a": "#f3f4f6", "bg_b": "#e5e7eb", "paper": "#ffffff", "paper_alt": "#f7f7fa", "ink": "#111827", "muted": "#6b7280", "accent": "#374151", "accent_2": "#6366f1", "line": "#d6d9df", "good": "#166534", "bad": "#b91c1c"},
    "violet": {"bg_a": "#f5f3ff", "bg_b": "#ede9fe", "paper": "#fcfbff", "paper_alt": "#f3f0ff", "ink": "#231942", "muted": "#6c5b8c", "accent": "#7c3aed", "accent_2": "#c084fc", "line": "#ded7fb", "good": "#15803d", "bad": "#be123c"},
    "copper": {"bg_a": "#fff3eb", "bg_b": "#f7decd", "paper": "#fffaf7", "paper_alt": "#fff0e7", "ink": "#332117", "muted": "#7b5c4b", "accent": "#c9733d", "accent_2": "#fb923c", "line": "#efd4c2", "good": "#166534", "bad": "#b91c1c"},
    "teal": {"bg_a": "#ebfbfb", "bg_b": "#d6f3f1", "paper": "#fbffff", "paper_alt": "#edfbfa", "ink": "#153233", "muted": "#4a7070", "accent": "#0f8f8f", "accent_2": "#2dd4bf", "line": "#c8e9e7", "good": "#15803d", "bad": "#b91c1c"},
}


def _with_variant(palette: dict, shadow: str, texture: str, badge_fill: str) -> dict:
    data = dict(palette)
    data["shadow"] = shadow
    data["texture"] = texture
    data["badge_fill"] = badge_fill
    return data


def _build_theme_library() -> dict:
    themes = {}
    for name, palette in _BASE_THEMES.items():
        themes[f"{name}-glass"] = _with_variant(
            palette,
            "0 26px 70px rgba(15, 23, 42, 0.16)",
            "radial-gradient(circle at top right, color-mix(in srgb, var(--accent) 24%, transparent), transparent 30%), linear-gradient(180deg, var(--bg-a) 0%, var(--bg-b) 100%)",
            "color-mix(in srgb, var(--accent) 12%, white)",
        )
        themes[f"{name}-soft"] = _with_variant(
            palette,
            "0 18px 45px rgba(15, 23, 42, 0.12)",
            "radial-gradient(circle at top left, color-mix(in srgb, var(--accent-2) 20%, transparent), transparent 30%), linear-gradient(180deg, var(--bg-a) 0%, var(--bg-b) 100%)",
            "color-mix(in srgb, var(--accent-2) 15%, white)",
        )
        themes[f"{name}-ink"] = _with_variant(
            palette,
            "0 22px 60px rgba(15, 23, 42, 0.18)",
            "linear-gradient(135deg, color-mix(in srgb, var(--accent) 7%, var(--bg-a)) 0%, var(--bg-b) 100%)",
            "color-mix(in srgb, var(--accent) 18%, white)",
        )
    return themes


THEMES = _build_theme_library()


def pick_theme(seed: str = "", template_name: str = "") -> dict:
    names = sorted(THEMES.keys())
    source = f"{template_name}|{seed or 'artificial-teacher'}"
    idx = int(sha256(source.encode("utf-8")).hexdigest()[:8], 16) % len(names)
    theme_name = names[idx]
    return {"name": theme_name, **THEMES[theme_name]}


def prepare_context(template_name: str, context: dict) -> dict:
    prepared = dict(context or {})
    seed = str(prepared.get("theme_seed") or prepared.get("report_id") or prepared.get("title") or template_name)
    prepared.setdefault("theme", pick_theme(seed, template_name))
    prepared.setdefault("brand_name", "Artificial Teacher")
    prepared.setdefault("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    prepared.setdefault("report_id", sha256(seed.encode("utf-8")).hexdigest()[:10].upper())
    return prepared


def render_html(template_name: str, context: dict) -> str:
    template = _env.get_template(template_name)
    return template.render(**prepare_context(template_name, context))


def render_html_document(template_name: str, context: dict, filename: str) -> BytesIO:
    html = render_html(template_name, context)
    buffer = BytesIO(html.encode("utf-8"))
    buffer.name = filename
    buffer.seek(0)
    return buffer


def html_open_guide() -> str:
    return "HTML qo'llanma tayyor. Faylni brauzerda oching."
