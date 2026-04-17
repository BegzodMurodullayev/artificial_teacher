"""Group games center and multiplayer game flows, including Mafia."""

import json
import random
import re
import time
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from database.db import (
    add_group_game_points,
    clear_group_game,
    get_active_group_games,
    get_group_game,
    get_group_game_scores,
    get_group_game_settings,
    reset_group_game_scores,
    save_group_game,
    update_group_game_setting,
)

GAME_JOB_PREFIX = "group_game_timeout"
MAFIA_WAITING_SECONDS = 120
MAFIA_WIN_POINTS = {
    "civilian": 50,
    "doctor": 75,
    "commissioner": 100,
    "mafia": 100,
}
MAFIA_CORRECT_VOTE_POINTS = 25

WORD_GAME_BANK = [
    {"mode": "antonym", "prompt": "Katta", "accepted": ["kichik", "kichkina", "mayda"]},
    {"mode": "antonym", "prompt": "Yaxshi", "accepted": ["yomon", "bad"]},
    {"mode": "antonym", "prompt": "Issiq", "accepted": ["sovuq", "salqin"]},
    {"mode": "antonym", "prompt": "Baland", "accepted": ["past", "quyi"]},
    {"mode": "antonym", "prompt": "Uzun", "accepted": ["qisqa", "kalta"]},
    {"mode": "synonym", "prompt": "Chiroyli", "accepted": ["go'zal", "suluv", "dilbar"]},
    {"mode": "synonym", "prompt": "Aqlli", "accepted": ["ziyrak", "donishmand", "bilmli"]},
    {"mode": "synonym", "prompt": "Jasur", "accepted": ["botir", "mard", "qo'rqmas"]},
    {"mode": "synonym", "prompt": "Do'st", "accepted": ["og'ayni", "safdosh", "yor"]},
]

ERROR_GAME_BANK = [
    {
        "wrong": "He go to school yesterday.",
        "error": "go",
        "correct": "went",
        "explanation": "Yesterday ishlatilgani uchun fe'l V2 bo'lishi kerak.",
    },
    {
        "wrong": "She don't like apples.",
        "error": "don't",
        "correct": "doesn't",
        "explanation": "She/He/It bilan doesn't ishlatiladi.",
    },
    {
        "wrong": "I am agree with you.",
        "error": "am agree",
        "correct": "agree",
        "explanation": "Agree fe'l, oldidan am ishlatilmaydi.",
    },
    {
        "wrong": "I have a apple.",
        "error": "a apple",
        "correct": "an apple",
        "explanation": "Unli tovush bilan boshlansa an ishlatiladi.",
    },
    {
        "wrong": "She is good in math.",
        "error": "in",
        "correct": "at",
        "explanation": "Good at - tayyor birikma.",
    },
]

TRANSLATION_GAME_BANK = [
    {
        "source": "Men bugun do'stlarim bilan kinoga bordim.",
        "accepted": [
            "i went to the cinema with my friends today",
            "i went to the movies with my friends today",
        ],
    },
    {
        "source": "U har kuni ertalab inglizcha mashq qiladi.",
        "accepted": [
            "he practices english every morning",
            "she practices english every morning",
        ],
    },
    {
        "source": "Biz kecha yangi loyiha ustida ishladik.",
        "accepted": [
            "we worked on a new project yesterday",
            "we worked on the new project yesterday",
        ],
    },
    {
        "source": "Men bu mavzuni yana tushuntirib bera olaman.",
        "accepted": [
            "i can explain this topic again",
            "i can explain this subject again",
        ],
    },
]


def _normalize_text(text: str) -> str:
    raw = (text or "").strip().lower()
    raw = raw.replace("’", "'").replace("ʻ", "'").replace("ʼ", "'").replace("`", "'")
    raw = re.sub(r"[^a-z0-9@\-' ]+", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def _escape_md(text: str) -> str:
    return re.sub(r"([_*\[\]()~`>#+=|{}.!-])", r"\\\1", str(text or ""))


def _display_name(user) -> str:
    if not user:
        return "User"
    if user.username:
        return f"@{user.username}"
    return user.first_name or "User"


def _job_name(chat_id: int) -> str:
    return f"{GAME_JOB_PREFIX}_{chat_id}"


def _load_payload(row: dict | None) -> dict[str, Any]:
    if not row:
        return {}
    payload = row.get("payload") or "{}"
    if isinstance(payload, dict):
        return payload
    try:
        data = json.loads(payload)
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


def _remove_timeout_jobs(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    if not getattr(context, "job_queue", None):
        return
    for job in context.job_queue.get_jobs_by_name(_job_name(chat_id)):
        try:
            job.schedule_removal()
        except Exception:
            pass


def games_center_text(group_mode: bool = False) -> str:
    prefix = "👥 *Guruh o'yinlari markazi*" if group_mode else "🎮 *O'yinlar markazi*"
    return (
        f"{prefix}\n\n"
        "*Hozir ishlaydigan o'yinlar:*\n"
        "- `/start_game word` yoki `/start_game antonym`\n"
        "- `/start_game synonym`\n"
        "- `/start_game error`\n"
        "- `/start_game translation`\n"
        "- `/start_game mafia`\n\n"
        "*Mafia oqimi:*\n"
        "- Ro'yxatdan o'tish: `/join`, `/leave`\n"
        "- Tun buyruqlari: `/kill`, `/heal`, `/check`, `/skip`\n"
        "- Kun buyruqlari: `/vote`, `/skip`\n"
        "- Roli qayta ko'rish: `/my_role` (private)\n\n"
        "*Boshqaruv:*\n"
        "- `/stop_game`\n"
        "- `/game_stats`\n"
        "- `/game_settings`\n"
        "- `/set_game_time <word|error|translation|mafia_night|mafia_day> <soniya>`\n"
        "- `/set_game_points <word|error> <ball>`\n"
        "- `/reset_game_scores`\n\n"
        "*Izoh:*\n"
        "- O'yinlar guruh ichida ishlaydi\n"
        "- To'g'ri javoblar uchun group leaderboard yuritiladi\n"
        "- Mafia roli private chatga yuboriladi, shuning uchun botga oldin `/start` bosilgan bo'lsa yaxshi"
    )


async def _reply(message, text: str) -> None:
    if message:
        await message.reply_text(text, parse_mode="Markdown")


async def _ensure_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or chat.type == "private":
        await _reply(update.effective_message, "Bu buyruq faqat guruh ichida ishlaydi.")
        return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
    except Exception:
        await _reply(update.effective_message, "Admin huquqini tekshirib bo'lmadi.")
        return False
    if member.status not in ("administrator", "creator"):
        await _reply(update.effective_message, "Bu buyruq faqat guruh adminlari uchun.")
        return False
    return True


async def games_center_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await _reply(update.effective_message, games_center_text(group_mode=bool(chat and chat.type != "private")))


def _build_word_prompt(entry: dict[str, Any], settings: dict[str, Any]) -> str:
    mode_label = "antonim" if entry["mode"] == "antonym" else "sinonim"
    return (
        f"🎯 *So'z topish o'yini*\n\n"
        f"So'z: *{_escape_md(entry['prompt'])}*\n"
        f"Vazifa: shu so'zning *{mode_label}*ini yozing.\n\n"
        f"Vaqt: *{settings['word_time_limit']} soniya*\n"
        f"To'g'ri javob: *+{settings['word_points']} ball*\n"
        f"Birinchi bo'lsa: qo'shimcha *+5 ball*"
    )


def _build_error_prompt(entry: dict[str, Any], settings: dict[str, Any]) -> str:
    return (
        f"❌ *Xatoni top*\n\n"
        f"Gap: `{_escape_md(entry['wrong'])}`\n\n"
        "Format: `xato -> to'g'ri`\n"
        "Masalan: `go -> went`\n\n"
        f"Vaqt: *{settings['error_time_limit']} soniya*\n"
        f"To'g'ri javob: *+{settings['error_points']} ball*"
    )


def _build_translation_prompt(entry: dict[str, Any], settings: dict[str, Any]) -> str:
    return (
        f"🏃 *Tarjima poygasi*\n\n"
        f"O'zbekcha gap:\n`{_escape_md(entry['source'])}`\n\n"
        "Uni inglizchaga tarjima qiling.\n"
        f"Vaqt: *{settings['translation_time_limit']} soniya*\n"
        f"A'lo tarjima: *+{settings['translation_points_perfect']} ball*"
    )


def _build_session_payload(game_key: str, entry: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    now = int(time.time())
    if game_key in {"word", "antonym", "synonym"}:
        seconds = int(settings["word_time_limit"])
        prompt = _build_word_prompt(entry, settings)
    elif game_key == "error":
        seconds = int(settings["error_time_limit"])
        prompt = _build_error_prompt(entry, settings)
    else:
        seconds = int(settings["translation_time_limit"])
        prompt = _build_translation_prompt(entry, settings)
    return {
        "entry": entry,
        "prompt": prompt,
        "winners": [],
        "started_at": now,
        "ends_at": now + seconds,
    }


async def _schedule_timeout(context: ContextTypes.DEFAULT_TYPE, chat_id: int, seconds: int):
    if not getattr(context, "job_queue", None):
        return
    _remove_timeout_jobs(context, chat_id)
    context.job_queue.run_once(
        _game_timeout_job,
        when=max(5, int(seconds)),
        name=_job_name(chat_id),
        data={"chat_id": chat_id},
    )


def _new_mafia_player(user) -> dict[str, Any]:
    return {
        "user_id": int(user.id),
        "username": str(user.username or ""),
        "display_name": _display_name(user),
        "role": "",
        "is_alive": True,
        "joined_at": int(time.time()),
        "dm_ok": None,
    }


def _mafia_player_name(player: dict[str, Any]) -> str:
    return player.get("display_name") or (f"@{player.get('username')}" if player.get("username") else f"user_{player.get('user_id')}")


def _alive_players(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [player for player in payload.get("players", []) if player.get("is_alive", True)]


def _alive_players_by_role(payload: dict[str, Any], role: str) -> list[dict[str, Any]]:
    return [player for player in _alive_players(payload) if player.get("role") == role]


def _find_player(payload: dict[str, Any], user_id: int) -> dict[str, Any] | None:
    for player in payload.get("players", []):
        if int(player.get("user_id", 0)) == int(user_id):
            return player
    return None


def _eligible_targets(payload: dict[str, Any], action: str, actor_id: int | None = None) -> list[dict[str, Any]]:
    players = _alive_players(payload)
    if action == "kill":
        return [player for player in players if player.get("role") != "mafia"]
    if action == "check":
        return [player for player in players if int(player.get("user_id", 0)) != int(actor_id or 0)]
    if action == "vote":
        return [player for player in players if int(player.get("user_id", 0)) != int(actor_id or 0)]
    return players


def _format_target_lines(players: list[dict[str, Any]]) -> str:
    if not players:
        return "- nishon yo'q"
    return "\n".join(f"{idx}. {_escape_md(_mafia_player_name(player))}" for idx, player in enumerate(players, start=1))


def _resolve_target(text: str, players: list[dict[str, Any]]) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(players):
            return players[idx - 1]

    normalized = _normalize_text(raw).lstrip("@")
    partial_match = None
    for player in players:
        keys = {
            _normalize_text(_mafia_player_name(player)).lstrip("@"),
            _normalize_text(player.get("username", "")).lstrip("@"),
            _normalize_text(player.get("display_name", "")).lstrip("@"),
        }
        keys = {key for key in keys if key}
        if normalized in keys:
            return player
        if not partial_match and any(normalized and normalized in key for key in keys):
            partial_match = player
    return partial_match


def _mafia_roles_for_count(count: int) -> list[str]:
    mafia_count = 2 if count < 10 else 3
    roles = ["mafia"] * mafia_count + ["commissioner"] + ["doctor"]
    roles.extend(["civilian"] * max(0, count - len(roles)))
    random.shuffle(roles)
    return roles


def _build_waiting_payload(created_by: int) -> dict[str, Any]:
    now = int(time.time())
    return {
        "created_by": int(created_by),
        "players": [],
        "round": 0,
        "waiting_ends_at": now + MAFIA_WAITING_SECONDS,
        "night_actions": {},
        "day_votes": {},
        "last_check": {},
    }


def _build_waiting_text(chat_id: int, payload: dict[str, Any], settings: dict[str, Any]) -> str:
    players = payload.get("players", [])
    lines = [
        "🕵️ *Mafia ro'yxatdan o'tishi ochildi*",
        "",
        f"Guruh: `{chat_id}`",
        f"Ishtirokchilar: *{len(players)}/{settings['mafia_max_players']}*",
        f"Boshlash uchun minimum: *{settings['mafia_min_players']}*",
        f"Avto start: *{MAFIA_WAITING_SECONDS} soniya*",
        "",
        "Qo'shilish: `/join`",
        "Chiqish: `/leave`",
        "Admin erta boshlashi mumkin: `/start_game mafia`",
    ]
    if players:
        lines.append("")
        lines.append("*Ro'yxat:*")
        for idx, player in enumerate(players, start=1):
            lines.append(f"{idx}. {_escape_md(_mafia_player_name(player))}")
    return "\n".join(lines)


def _build_role_message(player: dict[str, Any], payload: dict[str, Any]) -> str:
    role = player.get("role")
    role_title = {
        "mafia": "🔪 Mafia",
        "commissioner": "🔍 Komissar",
        "doctor": "⚕️ Shifokor",
        "civilian": "🙂 Tinch aholi",
    }.get(role, "🎭 Ishtirokchi")
    lines = [
        "🕵️ *Mafia o'yini boshlandi*",
        "",
        f"Sizning rol: *{role_title}*",
    ]
    if role == "mafia":
        teammates = [item for item in payload.get("players", []) if item.get("role") == "mafia" and int(item.get("user_id", 0)) != int(player.get("user_id", 0))]
        if teammates:
            lines.append(f"Sheriklar: {', '.join(_escape_md(_mafia_player_name(item)) for item in teammates)}")
    elif role == "commissioner":
        lines.append("Har tun bir odamni tekshirasiz: `/check <raqam>`")
    elif role == "doctor":
        lines.append("Har tun bir odamni saqlaysiz: `/heal <raqam>`")
    else:
        lines.append("Kun davomida kuzatib, to'g'ri odamga ovoz bering.")
    lines.extend(
        [
            "",
            "Private buyruqlar:",
            "- `/my_role`",
            "- `/kill <raqam>` yoki `/kill @username`",
            "- `/heal <raqam>`",
            "- `/check <raqam>`",
            "- `/vote <raqam>`",
            "- `/skip`",
        ]
    )
    return "\n".join(lines)


async def _send_role_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int, payload: dict[str, Any]) -> list[dict[str, Any]]:
    failed = []
    for player in payload.get("players", []):
        try:
            await context.bot.send_message(player["user_id"], _build_role_message(player, payload), parse_mode="Markdown")
            player["dm_ok"] = True
        except Exception:
            player["dm_ok"] = False
            failed.append(player)
    save_group_game(chat_id, "mafia", "night", payload)
    return failed


async def _send_mafia_night_prompts(context: ContextTypes.DEFAULT_TYPE, chat_id: int, payload: dict[str, Any], settings: dict[str, Any]) -> list[dict[str, Any]]:
    failed = []
    mafia_targets = _eligible_targets(payload, "kill")
    alive_players = _alive_players(payload)
    for player in alive_players:
        role = player.get("role")
        text = None
        if role == "mafia":
            text = (
                f"🌙 *Tun {payload.get('round', 1)}*\n\n"
                "Kimni yo'qotmoqchisiz?\n"
                f"{_format_target_lines(mafia_targets)}\n\n"
                "Buyruq: `/kill <raqam>`\n"
                "Agar kutmoqchi bo'lsangiz: `/skip`"
            )
        elif role == "commissioner":
            targets = _eligible_targets(payload, "check", player["user_id"])
            text = (
                f"🌙 *Tun {payload.get('round', 1)}*\n\n"
                "Kimni tekshirmoqchisiz?\n"
                f"{_format_target_lines(targets)}\n\n"
                "Buyruq: `/check <raqam>`\n"
                "O'tkazib yuborish: `/skip`"
            )
        elif role == "doctor":
            targets = _eligible_targets(payload, "heal", player["user_id"])
            text = (
                f"🌙 *Tun {payload.get('round', 1)}*\n\n"
                "Kimni saqlamoqchisiz?\n"
                f"{_format_target_lines(targets)}\n\n"
                "Buyruq: `/heal <raqam>`\n"
                "O'tkazib yuborish: `/skip`"
            )
        if not text:
            continue
        try:
            await context.bot.send_message(player["user_id"], text, parse_mode="Markdown")
        except Exception:
            failed.append(player)
    return failed


def _night_actions_ready(payload: dict[str, Any]) -> bool:
    actions = payload.get("night_actions", {})
    mafia_ids = {int(player["user_id"]) for player in _alive_players_by_role(payload, "mafia")}
    mafia_votes = {int(uid): int(target) for uid, target in (actions.get("mafia_votes") or {}).items()}
    if not mafia_ids or not mafia_ids.issubset(set(mafia_votes.keys())):
        return False

    doctor = _alive_players_by_role(payload, "doctor")
    if doctor and "doctor_heal" not in actions:
        return False

    commissioner = _alive_players_by_role(payload, "commissioner")
    if commissioner and "commissioner_check" not in actions:
        return False

    return True


def _day_votes_ready(payload: dict[str, Any]) -> bool:
    alive_ids = {int(player["user_id"]) for player in _alive_players(payload)}
    votes = {int(uid) for uid in (payload.get("day_votes") or {}).keys()}
    return bool(alive_ids) and alive_ids.issubset(votes)


def _resolve_night(payload: dict[str, Any]) -> dict[str, Any]:
    actions = payload.get("night_actions") or {}
    mafia_votes = actions.get("mafia_votes") or {}
    vote_counts: dict[int, int] = {}
    for target in mafia_votes.values():
        target_id = int(target or 0)
        vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

    kill_target = None
    if vote_counts:
        ordered = sorted(vote_counts.items(), key=lambda item: (-item[1], item[0]))
        kill_target = int(ordered[0][0] or 0) or None

    heal_target = int(actions.get("doctor_heal") or 0) or None
    check_target = int(actions.get("commissioner_check") or 0) or None

    saved = bool(kill_target and heal_target and kill_target == heal_target)
    killed_player = None
    if kill_target and not saved:
        killed_player = _find_player(payload, kill_target)
        if killed_player:
            killed_player["is_alive"] = False
            killed_player["death_round"] = int(payload.get("round", 1))
            killed_player["death_phase"] = "night"

    return {
        "kill_target": kill_target,
        "heal_target": heal_target,
        "check_target": check_target,
        "saved": saved,
        "killed_player": killed_player,
    }


def _check_mafia_winner(payload: dict[str, Any]) -> str | None:
    mafia_alive = len(_alive_players_by_role(payload, "mafia"))
    town_alive = len([player for player in _alive_players(payload) if player.get("role") != "mafia"])
    if mafia_alive <= 0:
        return "town"
    if mafia_alive >= town_alive:
        return "mafia"
    return None


def _alive_roster_text(payload: dict[str, Any]) -> str:
    players = _alive_players(payload)
    if not players:
        return "-"
    return "\n".join(f"{idx}. {_escape_md(_mafia_player_name(player))}" for idx, player in enumerate(players, start=1))


def _build_day_intro(payload: dict[str, Any], night_result: dict[str, Any], settings: dict[str, Any]) -> str:
    killed_player = night_result.get("killed_player")
    if killed_player:
        death_line = f"💀 Tunda {_escape_md(_mafia_player_name(killed_player))} yo'qotildi."
    elif night_result.get("saved"):
        target = _find_player(payload, int(night_result.get("kill_target") or 0))
        death_line = f"🛡 Shifokor {_escape_md(_mafia_player_name(target))}ni saqlab qoldi." if target else "🛡 Shifokor hujumni qaytardi."
    else:
        death_line = "🌅 Bu tun hech kim o'lmadi."

    lines = [
        f"☀️ *Kun {payload.get('round', 1)} boshlandi*",
        "",
        death_line,
        "",
        "*Tirik o'yinchilar:*",
        _alive_roster_text(payload),
        "",
        f"Ovoz berish vaqti: *{settings['mafia_day_time']} soniya*",
        "Buyruq: `/vote <raqam>` yoki `/skip`",
    ]
    return "\n".join(lines)


def _resolve_day_votes(payload: dict[str, Any]) -> dict[str, Any]:
    votes = payload.get("day_votes") or {}
    counts: dict[int, int] = {}
    for target in votes.values():
        target_id = int(target or 0)
        if target_id <= 0:
            continue
        counts[target_id] = counts.get(target_id, 0) + 1

    if not counts:
        return {"eliminated": None, "counts": counts, "tie": False}

    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    if len(ordered) >= 2 and ordered[0][1] == ordered[1][1]:
        return {"eliminated": None, "counts": counts, "tie": True}

    eliminated = _find_player(payload, int(ordered[0][0]))
    if eliminated:
        eliminated["is_alive"] = False
        eliminated["death_round"] = int(payload.get("round", 1))
        eliminated["death_phase"] = "day"
    return {"eliminated": eliminated, "counts": counts, "tie": False}


async def _award_correct_voters(chat_id: int, payload: dict[str, Any], eliminated: dict[str, Any] | None) -> None:
    if not eliminated:
        return
    target_id = int(eliminated.get("user_id", 0) or 0)
    if not target_id:
        return
    for voter_id, vote_target in (payload.get("day_votes") or {}).items():
        if int(vote_target or 0) != target_id:
            continue
        voter = _find_player(payload, int(voter_id))
        if not voter:
            continue
        add_group_game_points(chat_id, voter["user_id"], _mafia_player_name(voter), MAFIA_CORRECT_VOTE_POINTS, won=0)


def _build_day_result_text(payload: dict[str, Any], vote_result: dict[str, Any]) -> str:
    eliminated = vote_result.get("eliminated")
    counts = vote_result.get("counts") or {}
    lines = [f"📊 *Kun {payload.get('round', 1)} yakuni*"]
    if counts:
        lines.append("")
        lines.append("*Ovozlar:*")
        for target_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            target = _find_player(payload, int(target_id))
            if target:
                lines.append(f"- {_escape_md(_mafia_player_name(target))}: *{count}* ovoz")
    if eliminated:
        role_label = {
            "mafia": "Mafia",
            "commissioner": "Komissar",
            "doctor": "Shifokor",
            "civilian": "Tinch aholi",
        }.get(eliminated.get("role"), eliminated.get("role", "noma'lum"))
        lines.extend(
            [
                "",
                f"💀 {_escape_md(_mafia_player_name(eliminated))} chiqarildi.",
                f"Roli: *{role_label}*",
            ]
        )
    elif vote_result.get("tie"):
        lines.extend(["", "⚖️ Ovozlar teng bo'ldi. Hech kim chiqarilmadi."])
    else:
        lines.extend(["", "🤷 Bu safar hech kimga yetarli ovoz berilmadi."])
    return "\n".join(lines)


def _build_mafia_final_text(payload: dict[str, Any], winner: str) -> str:
    title = "🏆 *Tinch aholi g'alaba qozondi!*" if winner == "town" else "🏆 *Mafia g'alaba qozondi!*"
    lines = [title, ""]
    if winner == "town":
        lines.append("Barcha mafiya topildi.")
    else:
        lines.append("Mafia soni qolgan tinch aholi soniga yetdi.")
    lines.extend(["", "*Rollar:*"])
    for player in payload.get("players", []):
        role_label = {
            "mafia": "Mafia",
            "commissioner": "Komissar",
            "doctor": "Shifokor",
            "civilian": "Tinch aholi",
        }.get(player.get("role"), player.get("role", "noma'lum"))
        state = "tirik" if player.get("is_alive", True) else "o'lgan"
        lines.append(f"- {_escape_md(_mafia_player_name(player))}: *{role_label}* ({state})")
    return "\n".join(lines)


def _reward_mafia_winners(chat_id: int, payload: dict[str, Any], winner: str) -> None:
    for player in payload.get("players", []):
        role = player.get("role")
        alive = bool(player.get("is_alive", True))
        if winner == "town" and role == "mafia":
            continue
        if winner == "mafia" and role != "mafia":
            continue
        if winner == "town" and not alive:
            continue
        points = int(MAFIA_WIN_POINTS.get(role, 40))
        add_group_game_points(chat_id, player["user_id"], _mafia_player_name(player), points, won=1)


async def _start_mafia_night(context: ContextTypes.DEFAULT_TYPE, chat_id: int, payload: dict[str, Any], settings: dict[str, Any]):
    payload["night_actions"] = {"mafia_votes": {}}
    payload["day_votes"] = {}
    payload["phase_started_at"] = int(time.time())
    payload["phase_ends_at"] = int(time.time()) + int(settings["mafia_night_time"])
    save_group_game(chat_id, "mafia", "night", payload)

    await context.bot.send_message(
        chat_id,
        (
            f"🌙 *Tun {payload.get('round', 1)} boshlandi*\n\n"
            "Shahar uxlayapti.\n"
            "Mafia, shifokor va komissar private chatda harakat qiladi.\n"
            f"Tun vaqti: *{settings['mafia_night_time']} soniya*"
        ),
        parse_mode="Markdown",
    )
    failed = await _send_mafia_night_prompts(context, chat_id, payload, settings)
    if failed:
        failed_names = ", ".join(_escape_md(_mafia_player_name(player)) for player in failed)
        await context.bot.send_message(
            chat_id,
            (
                "⚠️ Quyidagilarga private xabar yuborib bo'lmadi:\n"
                f"{failed_names}\n\n"
                "Ular botga private `/start` bosib, keyin `/my_role` orqali rolini ko'rsin."
            ),
            parse_mode="Markdown",
        )
    await _schedule_timeout(context, chat_id, int(settings["mafia_night_time"]))


async def _start_mafia_day(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    payload: dict[str, Any],
    settings: dict[str, Any],
    night_result: dict[str, Any],
):
    winner = _check_mafia_winner(payload)
    if winner:
        _reward_mafia_winners(chat_id, payload, winner)
        clear_group_game(chat_id)
        await context.bot.send_message(chat_id, _build_mafia_final_text(payload, winner), parse_mode="Markdown")
        return

    payload["day_votes"] = {}
    payload["phase_started_at"] = int(time.time())
    payload["phase_ends_at"] = int(time.time()) + int(settings["mafia_day_time"])
    save_group_game(chat_id, "mafia", "day", payload)
    await context.bot.send_message(chat_id, _build_day_intro(payload, night_result, settings), parse_mode="Markdown")
    await _schedule_timeout(context, chat_id, int(settings["mafia_day_time"]))


async def _begin_next_mafia_round(context: ContextTypes.DEFAULT_TYPE, chat_id: int, payload: dict[str, Any], settings: dict[str, Any]):
    payload["round"] = int(payload.get("round", 1)) + 1
    await _start_mafia_night(context, chat_id, payload, settings)


async def _finish_mafia_night(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    session = get_group_game(chat_id)
    if not session or session.get("game_type") != "mafia" or session.get("status") != "night":
        return
    payload = _load_payload(session)
    settings = get_group_game_settings(chat_id)
    result = _resolve_night(payload)
    await _start_mafia_day(context, chat_id, payload, settings, result)


async def _finish_mafia_day(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    session = get_group_game(chat_id)
    if not session or session.get("game_type") != "mafia" or session.get("status") != "day":
        return
    payload = _load_payload(session)
    settings = get_group_game_settings(chat_id)
    result = _resolve_day_votes(payload)
    await _award_correct_voters(chat_id, payload, result.get("eliminated"))

    await context.bot.send_message(chat_id, _build_day_result_text(payload, result), parse_mode="Markdown")
    winner = _check_mafia_winner(payload)
    if winner:
        _reward_mafia_winners(chat_id, payload, winner)
        clear_group_game(chat_id)
        await context.bot.send_message(chat_id, _build_mafia_final_text(payload, winner), parse_mode="Markdown")
        return

    save_group_game(chat_id, "mafia", "day", payload)
    await _begin_next_mafia_round(context, chat_id, payload, settings)


async def _maybe_finish_mafia_night(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    session = get_group_game(chat_id)
    if not session or session.get("game_type") != "mafia" or session.get("status") != "night":
        return
    payload = _load_payload(session)
    if not _night_actions_ready(payload):
        return
    _remove_timeout_jobs(context, chat_id)
    await _finish_mafia_night(context, chat_id)


async def _maybe_finish_mafia_day(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    session = get_group_game(chat_id)
    if not session or session.get("game_type") != "mafia" or session.get("status") != "day":
        return
    payload = _load_payload(session)
    if not _day_votes_ready(payload):
        return
    _remove_timeout_jobs(context, chat_id)
    await _finish_mafia_day(context, chat_id)


async def _start_mafia_match(context: ContextTypes.DEFAULT_TYPE, chat_id: int, payload: dict[str, Any], settings: dict[str, Any]):
    players = payload.get("players", [])
    if len(players) < int(settings["mafia_min_players"]):
        return False

    roles = _mafia_roles_for_count(len(players))
    for player, role in zip(players, roles):
        player["role"] = role
        player["is_alive"] = True

    payload["round"] = 1
    payload["night_actions"] = {"mafia_votes": {}}
    payload["day_votes"] = {}
    payload["last_check"] = {}
    save_group_game(chat_id, "mafia", "night", payload)

    failed = await _send_role_messages(context, chat_id, payload)
    await _start_mafia_night(context, chat_id, payload, settings)
    if failed:
        await context.bot.send_message(
            chat_id,
            "ℹ️ Rol xabari bormaganlar private botni ochib `/start`, keyin `/my_role` yozsin.",
            parse_mode="Markdown",
        )
    return True


async def start_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _ensure_group_admin(update, context):
        return

    chat = update.effective_chat
    requested = (_normalize_text(" ".join(context.args or [])) or "word").replace(" ", "_")
    alias_map = {
        "word": "word",
        "word_game": "word",
        "antonym": "antonym",
        "sinonim": "synonym",
        "synonym": "synonym",
        "error": "error",
        "xato": "error",
        "translation": "translation",
        "tarjima": "translation",
        "mafia": "mafia",
    }
    game_key = alias_map.get(requested)
    if not game_key:
        await _reply(
            update.effective_message,
            "Noma'lum o'yin. Misollar: `/start_game word`, `/start_game antonym`, `/start_game error`, `/start_game translation`, `/start_game mafia`",
        )
        return

    current = get_group_game(chat.id)
    settings = get_group_game_settings(chat.id)

    if game_key == "mafia":
        if current and current.get("game_type") == "mafia":
            if current.get("status") == "waiting":
                payload = _load_payload(current)
                if len(payload.get("players", [])) < int(settings["mafia_min_players"]):
                    await _reply(
                        update.effective_message,
                        f"Hali yetarli o'yinchi yo'q. Kamida *{settings['mafia_min_players']}* kishi kerak.",
                    )
                    return
                _remove_timeout_jobs(context, chat.id)
                await _start_mafia_match(context, chat.id, payload, settings)
                await _reply(update.effective_message, "✅ Mafia ro'yxati yopildi. Rollar tarqatildi.")
                return

            await _reply(update.effective_message, "Bu guruhda mafia allaqachon davom etyapti. Zarurat bo'lsa `/stop_game` bosing.")
            return

        if current:
            await _reply(update.effective_message, "Bu guruhda allaqachon aktiv o'yin bor. Avval `/stop_game` bosing.")
            return

        payload = _build_waiting_payload(update.effective_user.id)
        save_group_game(chat.id, "mafia", "waiting", payload)
        await _schedule_timeout(context, chat.id, MAFIA_WAITING_SECONDS)
        await _reply(update.effective_message, _build_waiting_text(chat.id, payload, settings))
        return

    if current:
        await _reply(update.effective_message, "Bu guruhda allaqachon aktiv o'yin bor. Avval `/stop_game` bosing.")
        return

    if game_key == "word":
        entry = random.choice(WORD_GAME_BANK)
    elif game_key == "antonym":
        entry = random.choice([row for row in WORD_GAME_BANK if row["mode"] == "antonym"])
    elif game_key == "synonym":
        entry = random.choice([row for row in WORD_GAME_BANK if row["mode"] == "synonym"])
    elif game_key == "error":
        entry = random.choice(ERROR_GAME_BANK)
    else:
        entry = random.choice(TRANSLATION_GAME_BANK)

    payload = _build_session_payload(game_key, entry, settings)
    save_group_game(chat.id, game_type=game_key, status="running", payload=payload)

    timeout_seconds = (
        settings["word_time_limit"]
        if game_key in {"word", "antonym", "synonym"}
        else settings["error_time_limit"]
        if game_key == "error"
        else settings["translation_time_limit"]
    )
    await _schedule_timeout(context, chat.id, int(timeout_seconds))
    await _reply(update.effective_message, payload["prompt"])


async def stop_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _ensure_group_admin(update, context):
        return
    chat = update.effective_chat
    current = get_group_game(chat.id)
    if not current:
        await _reply(update.effective_message, "Aktiv o'yin topilmadi.")
        return
    clear_group_game(chat.id)
    _remove_timeout_jobs(context, chat.id)
    await _reply(update.effective_message, f"🛑 `{current['game_type']}` o'yini to'xtatildi.")


async def game_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await _reply(update.effective_message, "Bu buyruq guruh ichida ishlaydi.")
        return
    settings = get_group_game_settings(chat.id)
    await _reply(
        update.effective_message,
        "⚙️ *O'yin sozlamalari*\n\n"
        f"So'z topish vaqti: *{settings['word_time_limit']} s*\n"
        f"So'z topish balli: *{settings['word_points']}*\n"
        f"Xatoni top vaqti: *{settings['error_time_limit']} s*\n"
        f"Xatoni top balli: *{settings['error_points']}*\n"
        f"Tarjima vaqti: *{settings['translation_time_limit']} s*\n"
        f"Tarjima perfect: *{settings['translation_points_perfect']} ball*\n"
        f"Tarjima partial: *{settings['translation_points_partial']} ball*\n"
        f"Mafia minimum: *{settings['mafia_min_players']}* kishi\n"
        f"Mafia maksimum: *{settings['mafia_max_players']}* kishi\n"
        f"Mafia tun vaqti: *{settings['mafia_night_time']} s*\n"
        f"Mafia kun vaqti: *{settings['mafia_day_time']} s*"
    )


async def set_game_time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _ensure_group_admin(update, context):
        return
    if len(context.args) < 2:
        await _reply(update.effective_message, "Format: `/set_game_time <word|error|translation|mafia_night|mafia_day> <soniya>`")
        return
    field_map = {
        "word": "word_time_limit",
        "error": "error_time_limit",
        "translation": "translation_time_limit",
        "mafia_night": "mafia_night_time",
        "mafia_day": "mafia_day_time",
    }
    target = _normalize_text(context.args[0])
    field = field_map.get(target)
    if not field:
        await _reply(update.effective_message, "Faqat `word`, `error`, `translation`, `mafia_night`, `mafia_day` bo'lishi mumkin.")
        return
    try:
        value = max(10, min(int(context.args[1]), 600))
    except ValueError:
        await _reply(update.effective_message, "Soniya raqam bo'lishi kerak.")
        return
    update_group_game_setting(update.effective_chat.id, field, value)
    await _reply(update.effective_message, f"✅ `{target}` uchun vaqt *{value} soniya* bo'ldi.")


async def set_game_points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _ensure_group_admin(update, context):
        return
    if len(context.args) < 2:
        await _reply(update.effective_message, "Format: `/set_game_points <word|error> <ball>`")
        return
    field_map = {
        "word": "word_points",
        "error": "error_points",
    }
    target = _normalize_text(context.args[0])
    field = field_map.get(target)
    if not field:
        await _reply(update.effective_message, "Faqat `word` yoki `error` bo'lishi mumkin.")
        return
    try:
        value = max(1, min(int(context.args[1]), 100))
    except ValueError:
        await _reply(update.effective_message, "Ball raqam bo'lishi kerak.")
        return
    update_group_game_setting(update.effective_chat.id, field, value)
    await _reply(update.effective_message, f"✅ `{target}` uchun ball *{value}* bo'ldi.")


async def reset_game_scores_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _ensure_group_admin(update, context):
        return
    reset_group_game_scores(update.effective_chat.id)
    await _reply(update.effective_message, "♻️ Guruh o'yin leaderboardi tozalandi.")


async def game_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await _reply(update.effective_message, "Bu buyruq guruh ichida ishlaydi.")
        return
    scores = get_group_game_scores(chat.id, limit=10)
    if not scores:
        await _reply(update.effective_message, "🏆 Hali o'yin ballari yig'ilmagan.")
        return
    lines = ["🏆 *Guruh o'yin leaderboardi*\n"]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for idx, row in enumerate(scores, start=1):
        prefix = medals.get(idx, f"{idx}.")
        name = _escape_md(row.get("username") or f"user_{row['user_id']}")
        lines.append(
            f"{prefix} *{name}* - {round(float(row.get('points', 0) or 0), 1)} ball | "
            f"{int(row.get('wins', 0) or 0)} win"
        )
    await _reply(update.effective_message, "\n".join(lines))


async def join_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await _reply(update.effective_message, "`/join` ni mafia ochilgan guruh ichida bosing.")
        return
    session = get_group_game(chat.id)
    if not session or session.get("game_type") != "mafia" or session.get("status") != "waiting":
        await _reply(update.effective_message, "Hozir bu guruhda ochiq mafia ro'yxati yo'q. Admin `/start_game mafia` yozsin.")
        return

    payload = _load_payload(session)
    settings = get_group_game_settings(chat.id)
    players = payload.setdefault("players", [])
    if _find_player(payload, update.effective_user.id):
        await _reply(update.effective_message, "Siz allaqachon ro'yxatdasiz.")
        return
    if len(players) >= int(settings["mafia_max_players"]):
        await _reply(update.effective_message, "Mafia ro'yxati to'ldi.")
        return

    players.append(_new_mafia_player(update.effective_user))
    save_group_game(chat.id, "mafia", "waiting", payload)

    if len(players) >= int(settings["mafia_max_players"]):
        _remove_timeout_jobs(context, chat.id)
        await _start_mafia_match(context, chat.id, payload, settings)
        await _reply(update.effective_message, "✅ Maksimal son to'ldi. Mafia darhol boshlandi.")
        return

    text = _build_waiting_text(chat.id, payload, settings)
    if len(players) >= int(settings["mafia_min_players"]):
        text += "\n\n✅ Minimum son yetdi. Admin istasa hozir `/start_game mafia` bilan darhol boshlashi mumkin."
    await _reply(update.effective_message, text)


async def leave_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await _reply(update.effective_message, "`/leave` faqat mafia ro'yxati ochiq bo'lganda guruh ichida ishlaydi.")
        return
    session = get_group_game(chat.id)
    if not session or session.get("game_type") != "mafia" or session.get("status") != "waiting":
        await _reply(update.effective_message, "Siz chiqadigan ochiq mafia ro'yxati topilmadi.")
        return

    payload = _load_payload(session)
    players = payload.get("players", [])
    before = len(players)
    players = [player for player in players if int(player.get("user_id", 0)) != int(update.effective_user.id)]
    if len(players) == before:
        await _reply(update.effective_message, "Siz ro'yxatda emassiz.")
        return
    payload["players"] = players
    save_group_game(chat.id, "mafia", "waiting", payload)
    await _reply(update.effective_message, _build_waiting_text(chat.id, payload, get_group_game_settings(chat.id)))


def _find_user_mafia_session(chat_id: int | None, user_id: int) -> tuple[dict[str, Any] | None, dict[str, Any], int | None]:
    if chat_id:
        session = get_group_game(chat_id)
        if session and session.get("game_type") == "mafia":
            payload = _load_payload(session)
            if _find_player(payload, user_id):
                return session, payload, chat_id
        return None, {}, chat_id
    for session in get_active_group_games("mafia", status=["waiting", "night", "day"]):
        payload = _load_payload(session)
        if _find_player(payload, user_id):
            return session, payload, int(session["chat_id"])
    return None, {}, None


def _extract_target_argument(context: ContextTypes.DEFAULT_TYPE) -> str:
    return " ".join(context.args or []).strip()


def _ensure_role_phase(
    session: dict[str, Any] | None,
    payload: dict[str, Any],
    user_id: int,
    expected_status: str,
    allowed_roles: set[str],
) -> tuple[dict[str, Any] | None, str | None]:
    if not session:
        return None, "Siz qatnashayotgan aktiv mafia topilmadi."
    if session.get("status") != expected_status:
        phase_label = {"waiting": "ro'yxatdan o'tish", "night": "tun", "day": "kun"}.get(session.get("status"), session.get("status"))
        return None, f"Hozir o'yin bosqichi: *{phase_label}*."
    player = _find_player(payload, user_id)
    if not player:
        return None, "Siz bu mafia o'yinida yo'qsiz."
    if not player.get("is_alive", True):
        return None, "Siz bu raundda endi faqat kuzatasiz."
    if player.get("role") not in allowed_roles:
        return None, "Bu buyruq sizning rolingiz uchun emas."
    return player, None


async def mafia_role_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    session, payload, group_chat_id = _find_user_mafia_session(None if not chat or chat.type == "private" else chat.id, update.effective_user.id)
    if not session:
        await _reply(update.effective_message, "Aktiv mafia topilmadi yoki siz ro'yxatda emassiz.")
        return
    player = _find_player(payload, update.effective_user.id)
    if not player or not player.get("role"):
        await _reply(update.effective_message, "Rol hali tarqatilmagan. Agar ro'yxat ochiq bo'lsa, boshlanishini kuting.")
        return

    text = _build_role_message(player, payload)
    if session.get("status") == "night" and player.get("is_alive", True):
        if player.get("role") == "mafia":
            text += "\n\n*Tungi nishonlar:*\n" + _format_target_lines(_eligible_targets(payload, "kill"))
        elif player.get("role") == "doctor":
            text += "\n\n*Davolash ro'yxati:*\n" + _format_target_lines(_eligible_targets(payload, "heal", player["user_id"]))
        elif player.get("role") == "commissioner":
            text += "\n\n*Tekshiruv ro'yxati:*\n" + _format_target_lines(_eligible_targets(payload, "check", player["user_id"]))
    elif session.get("status") == "day" and player.get("is_alive", True):
        text += "\n\n*Kunlik ovoz ro'yxati:*\n" + _format_target_lines(_eligible_targets(payload, "vote", player["user_id"]))
    if group_chat_id:
        text += f"\n\nGuruh ID: `{group_chat_id}`"
    await _reply(update.effective_message, text)


async def mafia_kill_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    session, payload, group_chat_id = _find_user_mafia_session(None if not chat or chat.type == "private" else chat.id, update.effective_user.id)
    player, error = _ensure_role_phase(session, payload, update.effective_user.id, "night", {"mafia"})
    if error:
        await _reply(update.effective_message, error)
        return

    target_text = _extract_target_argument(context)
    candidates = _eligible_targets(payload, "kill", update.effective_user.id)
    target = _resolve_target(target_text, candidates)
    if not target:
        await _reply(update.effective_message, "Nishon topilmadi. Misol: `/kill 2` yoki `/kill @username`")
        return

    payload.setdefault("night_actions", {}).setdefault("mafia_votes", {})[str(player["user_id"])] = int(target["user_id"])
    save_group_game(group_chat_id, "mafia", "night", payload)
    await _reply(update.effective_message, f"✅ Tungi ovozingiz qabul qilindi: *{_escape_md(_mafia_player_name(target))}*")
    await _maybe_finish_mafia_night(context, group_chat_id)


async def mafia_heal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    session, payload, group_chat_id = _find_user_mafia_session(None if not chat or chat.type == "private" else chat.id, update.effective_user.id)
    player, error = _ensure_role_phase(session, payload, update.effective_user.id, "night", {"doctor"})
    if error:
        await _reply(update.effective_message, error)
        return

    target_text = _extract_target_argument(context)
    candidates = _eligible_targets(payload, "heal", update.effective_user.id)
    target = _resolve_target(target_text, candidates)
    if not target:
        await _reply(update.effective_message, "Nishon topilmadi. Misol: `/heal 3` yoki `/heal @username`")
        return

    payload.setdefault("night_actions", {})["doctor_heal"] = int(target["user_id"])
    save_group_game(group_chat_id, "mafia", "night", payload)
    await _reply(update.effective_message, f"🛡 Saqlash harakatingiz qabul qilindi: *{_escape_md(_mafia_player_name(target))}*")
    await _maybe_finish_mafia_night(context, group_chat_id)


async def mafia_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    session, payload, group_chat_id = _find_user_mafia_session(None if not chat or chat.type == "private" else chat.id, update.effective_user.id)
    player, error = _ensure_role_phase(session, payload, update.effective_user.id, "night", {"commissioner"})
    if error:
        await _reply(update.effective_message, error)
        return

    target_text = _extract_target_argument(context)
    candidates = _eligible_targets(payload, "check", update.effective_user.id)
    target = _resolve_target(target_text, candidates)
    if not target:
        await _reply(update.effective_message, "Nishon topilmadi. Misol: `/check 4` yoki `/check @username`")
        return

    payload.setdefault("night_actions", {})["commissioner_check"] = int(target["user_id"])
    payload["last_check"] = {
        "target_id": int(target["user_id"]),
        "target_name": _mafia_player_name(target),
        "result": "mafia" if target.get("role") == "mafia" else "not_mafia",
    }
    save_group_game(group_chat_id, "mafia", "night", payload)
    result_text = "🟥 Mafia" if target.get("role") == "mafia" else "🟩 Mafia emas"
    await _reply(update.effective_message, f"🔍 Tekshiruv natijasi: *{_escape_md(_mafia_player_name(target))}* — {result_text}")
    await _maybe_finish_mafia_night(context, group_chat_id)


async def mafia_vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    session, payload, group_chat_id = _find_user_mafia_session(None if not chat or chat.type == "private" else chat.id, update.effective_user.id)
    player, error = _ensure_role_phase(session, payload, update.effective_user.id, "day", {"mafia", "commissioner", "doctor", "civilian"})
    if error:
        await _reply(update.effective_message, error)
        return

    target_text = _extract_target_argument(context)
    candidates = _eligible_targets(payload, "vote", update.effective_user.id)
    target = _resolve_target(target_text, candidates)
    if not target:
        await _reply(update.effective_message, "Ovoz nishoni topilmadi. Misol: `/vote 1` yoki `/vote @username`")
        return

    payload.setdefault("day_votes", {})[str(player["user_id"])] = int(target["user_id"])
    save_group_game(group_chat_id, "mafia", "day", payload)
    await _reply(update.effective_message, f"🗳 Ovoz qabul qilindi: *{_escape_md(_mafia_player_name(target))}*")
    await _maybe_finish_mafia_day(context, group_chat_id)


async def mafia_skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    session, payload, group_chat_id = _find_user_mafia_session(None if not chat or chat.type == "private" else chat.id, update.effective_user.id)
    if not session:
        await _reply(update.effective_message, "Aktiv mafia topilmadi.")
        return
    player = _find_player(payload, update.effective_user.id)
    if not player or not player.get("is_alive", True):
        await _reply(update.effective_message, "Siz bu bosqichda faol o'yinchi emassiz.")
        return

    if session.get("status") == "night":
        actions = payload.setdefault("night_actions", {})
        role = player.get("role")
        if role == "mafia":
            actions.setdefault("mafia_votes", {})[str(player["user_id"])] = 0
        elif role == "doctor":
            actions["doctor_heal"] = 0
        elif role == "commissioner":
            actions["commissioner_check"] = 0
        else:
            await _reply(update.effective_message, "Bu rol tun harakati qilmaydi.")
            return
        save_group_game(group_chat_id, "mafia", "night", payload)
        await _reply(update.effective_message, "⏭ Tungi harakatingiz o'tkazib yuborildi.")
        await _maybe_finish_mafia_night(context, group_chat_id)
        return

    if session.get("status") == "day":
        payload.setdefault("day_votes", {})[str(player["user_id"])] = 0
        save_group_game(group_chat_id, "mafia", "day", payload)
        await _reply(update.effective_message, "⏭ Siz bu kun uchun skip berdingiz.")
        await _maybe_finish_mafia_day(context, group_chat_id)
        return

    await _reply(update.effective_message, "Hozir skip ishlatiladigan faol bosqich yo'q.")


def _check_word_answer(text: str, entry: dict[str, Any]) -> dict[str, Any]:
    answer = _normalize_text(text)
    accepted = {_normalize_text(item) for item in entry.get("accepted", [])}
    if answer in accepted:
        return {"ok": True, "quality": "correct", "normalized": answer}
    return {"ok": False}


def _check_error_answer(text: str, entry: dict[str, Any]) -> dict[str, Any]:
    answer = _normalize_text(text)
    error_text = _normalize_text(entry["error"])
    correct_text = _normalize_text(entry["correct"])
    separators = ["->", "-", "/", ">", "→"]

    if answer == correct_text:
        return {"ok": False, "warn": "Faqat to'g'ri variantni emas, xato qismni ham ko'rsating. Masalan: `go -> went`"}

    for sep in separators:
        if sep in text:
            parts = [item.strip() for item in re.split(r"->|→|/|-|>", text, maxsplit=1) if item.strip()]
            if len(parts) == 2:
                left = _normalize_text(parts[0])
                right = _normalize_text(parts[1])
                if left == error_text and right == correct_text:
                    return {"ok": True, "quality": "correct"}
    return {"ok": False}


def _translation_score(answer: str, accepted_rows: list[str]) -> tuple[str, int]:
    normalized = _normalize_text(answer)
    accepted = [_normalize_text(item) for item in accepted_rows]
    if normalized in accepted:
        return "perfect", 100

    answer_tokens = set(normalized.split())
    best = 0
    for target in accepted:
        target_tokens = set(target.split())
        if not target_tokens:
            continue
        overlap = len(answer_tokens & target_tokens)
        score = round((overlap / len(target_tokens)) * 100)
        best = max(best, score)
    if best >= 80:
        return "good", best
    if best >= 55:
        return "partial", best
    return "wrong", best


def _check_translation_answer(text: str, entry: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    quality, score = _translation_score(text, entry.get("accepted", []))
    if quality == "perfect":
        return {"ok": True, "quality": quality, "points": int(settings["translation_points_perfect"])}
    if quality == "good":
        good_points = max(int(settings["translation_points_partial"]) + 5, int(settings["translation_points_perfect"]) - 5)
        return {"ok": True, "quality": quality, "points": good_points}
    if quality == "partial":
        return {"ok": True, "quality": quality, "points": int(settings["translation_points_partial"])}
    return {"ok": False}


async def handle_group_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    message = update.message
    if not message or not message.text:
        return False
    if message.text.startswith("/"):
        return False

    chat = update.effective_chat
    user = update.effective_user
    session = get_group_game(chat.id)
    if not session or session.get("status") != "running":
        return False

    payload = _load_payload(session)
    entry = payload.get("entry") or {}
    if not entry:
        return False

    winners = payload.setdefault("winners", [])
    if any(int(row.get("user_id", 0)) == int(user.id) for row in winners):
        return False

    settings = get_group_game_settings(chat.id)
    game_type = session.get("game_type")
    result: dict[str, Any] = {"ok": False}
    if game_type in {"word", "antonym", "synonym"}:
        result = _check_word_answer(message.text, entry)
        if result.get("ok"):
            base_points = int(settings["word_points"])
            bonus = 5 if not winners else 0
            result["points"] = base_points + bonus
            result["reply"] = (
                f"✅ {_escape_md(_display_name(user))} to'g'ri topdi: *{_escape_md(result['normalized'])}*"
                f"\nBall: *+{result['points']}*"
            )
    elif game_type == "error":
        result = _check_error_answer(message.text, entry)
        if result.get("warn"):
            await message.reply_text(result["warn"], parse_mode="Markdown")
            return True
        if result.get("ok"):
            base_points = int(settings["error_points"])
            bonus = 5 if not winners else 0
            result["points"] = base_points + bonus
            result["reply"] = (
                f"✅ {_escape_md(_display_name(user))} xatoni to'g'ri topdi!"
                f"\nBall: *+{result['points']}*"
            )
    elif game_type == "translation":
        result = _check_translation_answer(message.text, entry, settings)
        if result.get("ok"):
            quality_label = {
                "perfect": "A'lo tarjima",
                "good": "Yaxshi tarjima",
                "partial": "Qisman to'g'ri",
            }.get(result["quality"], "To'g'ri")
            result["reply"] = (
                f"✅ {_escape_md(_display_name(user))} - *{quality_label}*"
                f"\nBall: *+{result['points']}*"
            )

    if not result.get("ok"):
        return False

    winners.append(
        {
            "user_id": user.id,
            "username": _display_name(user),
            "answer": message.text.strip()[:160],
            "points": result["points"],
            "quality": result.get("quality", "correct"),
        }
    )
    payload["winners"] = winners
    save_group_game(chat.id, session["game_type"], session["status"], payload)
    add_group_game_points(
        chat.id,
        user.id,
        _display_name(user),
        result["points"],
        won=1 if len(winners) == 1 else 0,
    )
    await message.reply_text(result["reply"], parse_mode="Markdown")
    return True


def _build_game_result_text(game_type: str, payload: dict[str, Any], scores: list[dict[str, Any]]) -> str:
    entry = payload.get("entry") or {}
    winners = payload.get("winners") or []
    lines = []

    if game_type in {"word", "antonym", "synonym"}:
        lines.append("⏰ *So'z topish yakunlandi*")
        lines.append(f"So'z: *{_escape_md(entry.get('prompt', '-'))}*")
        lines.append(f"To'g'ri javoblar: `{_escape_md(', '.join(entry.get('accepted', [])))}`")
    elif game_type == "error":
        lines.append("⏰ *Xatoni top yakunlandi*")
        lines.append(f"Gap: `{_escape_md(entry.get('wrong', '-'))}`")
        lines.append(f"To'g'ri format: `{_escape_md(entry.get('error', '-'))} -> {_escape_md(entry.get('correct', '-'))}`")
        if entry.get("explanation"):
            lines.append(f"Izoh: {_escape_md(entry['explanation'])}")
    else:
        lines.append("⏰ *Tarjima poygasi yakunlandi*")
        lines.append(f"Gap: `{_escape_md(entry.get('source', '-'))}`")
        lines.append(f"Namuna tarjimalar: `{_escape_md('; '.join(entry.get('accepted', [])))}`")

    if winners:
        lines.append("")
        lines.append("*Winnerlar:*")
        for idx, winner in enumerate(winners[:5], start=1):
            lines.append(f"{idx}. {_escape_md(winner['username'])} - +{winner['points']} ball")
    else:
        lines.append("")
        lines.append("Bu safar to'g'ri javob topilmadi.")

    if scores:
        lines.append("")
        lines.append("*Top leaderboard:*")
        for idx, row in enumerate(scores[:3], start=1):
            name = _escape_md(row.get("username") or f"user_{row['user_id']}")
            lines.append(f"{idx}. {name} - {round(float(row.get('points', 0) or 0), 1)} ball")

    return "\n".join(lines)


async def _game_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data or {}
    chat_id = int(data.get("chat_id", 0) or 0)
    if not chat_id:
        return

    session = get_group_game(chat_id)
    if not session:
        return

    game_type = session.get("game_type")
    status = session.get("status")
    if game_type == "mafia":
        settings = get_group_game_settings(chat_id)
        payload = _load_payload(session)
        if status == "waiting":
            if len(payload.get("players", [])) >= int(settings["mafia_min_players"]):
                await _start_mafia_match(context, chat_id, payload, settings)
                await context.bot.send_message(chat_id, "⏱ Ro'yxatdan o'tish vaqti tugadi. Mafia avtomatik boshlandi.", parse_mode="Markdown")
            else:
                clear_group_game(chat_id)
                await context.bot.send_message(
                    chat_id,
                    f"⏱ Ro'yxatdan o'tish tugadi, lekin minimum *{settings['mafia_min_players']}* o'yinchi yig'ilmadi.",
                    parse_mode="Markdown",
                )
            return
        if status == "night":
            await _finish_mafia_night(context, chat_id)
            return
        if status == "day":
            await _finish_mafia_day(context, chat_id)
            return
        return

    if status != "running":
        return

    payload = _load_payload(session)
    scores = get_group_game_scores(chat_id, limit=3)
    text = _build_game_result_text(game_type, payload, scores)
    clear_group_game(chat_id)
    try:
        await context.bot.send_message(chat_id, text, parse_mode="Markdown")
    except Exception:
        pass
