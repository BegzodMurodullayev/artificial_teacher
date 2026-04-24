"""
Profile handler — /mystats, progress panel, learning statistics.
"""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.bot.utils.telegram import safe_reply, escape_html, fmt_num
from src.config import settings
from src.database.dao import stats_dao, subscription_dao, user_dao, reward_dao

logger = logging.getLogger(__name__)
router = Router(name="user_profile")


async def send_bonus_panel(message: Message, db_user: dict) -> None:
    """Show referral and bonus wallet information."""
    user_id = db_user["user_id"]
    wallet = await reward_dao.get_wallet(user_id)
    referral_code = wallet.get("referral_code", "")
    bot_username = settings.BOT_USERNAME.lstrip("@")
    invite_link = f"https://t.me/{bot_username}?start=ref_{referral_code}" if bot_username and referral_code else ""

    text = (
        "🎁 <b>Bonuslar va referral</b>\n\n"
        f"🎯 Ballar: <b>{fmt_num(int(wallet.get('points', 0)))}</b>\n"
        f"👥 Taklif qilingan userlar: <b>{fmt_num(wallet.get('total_referrals', 0))}</b>\n"
        f"🏷 Referral kod: <code>{escape_html(referral_code or 'yaratilmoqda')}</code>\n"
        "💸 Har bir referral uchun sizga <b>25 ball</b> qo'shiladi.\n\n"
    )
    if invite_link:
        text += f"🔗 Taklif havolasi:\n<code>{escape_html(invite_link)}</code>\n\n"
    text += (
        "Do'stingiz botga sizning havolangiz orqali kirsa, bonus balansingiz oshadi. "
        "Keyin bu tizim promo va premium imkoniyatlar bilan yanada kengayadi."
    )

    reply_markup = None
    if invite_link:
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Taklif linkini ochish", url=invite_link)]
            ]
        )
    await safe_reply(message, text, reply_markup=reply_markup)


@router.message(Command("mystats"))
async def cmd_mystats(message: Message, db_user: dict | None = None):
    """Show user's learning statistics."""
    if not db_user:
        return

    user_id = db_user["user_id"]
    stats = await stats_dao.get_stats(user_id)
    plan = await subscription_dao.get_user_plan(user_id)
    plan_name = await subscription_dao.get_active_plan_name(user_id)
    remaining = await subscription_dao.remaining_days(user_id)
    wallet = await reward_dao.get_wallet(user_id)
    usage = await stats_dao.get_usage_today(user_id)

    name = escape_html(db_user.get("first_name", "Student"))
    level = db_user.get("level", "A1")

    # Plan display
    plan_display = {
        "free": "Free ✨",
        "standard": "Standard ⭐",
        "pro": "Pro 💎",
        "premium": "Premium 👑",
    }.get(plan_name, plan_name.title())

    # Calculate quiz accuracy
    quiz_played = stats.get("quiz_played", 0)
    quiz_correct = stats.get("quiz_correct", 0)
    accuracy = f"{(quiz_correct / quiz_played * 100):.0f}%" if quiz_played > 0 else "—"

    # Build stats text
    text = (
        f"📊 <b>{name} — Statistika</b>\n\n"
        f"🎓 Daraja: <b>{level}</b>\n"
        f"📋 Reja: <b>{plan_display}</b>"
    )

    if plan_name != "free" and remaining > 0:
        text += f" ({remaining} kun qoldi)"
    text += "\n"

    text += (
        f"\n📝 <b>Faoliyat:</b>\n"
        f"  ✅ Tekshiruvlar: <b>{fmt_num(stats.get('checks_total', 0))}</b>\n"
        f"  🌐 Tarjimalar: <b>{fmt_num(stats.get('translations_total', 0))}</b>\n"
        f"  🔊 Talaffuz: <b>{fmt_num(stats.get('pron_total', 0))}</b>\n"
        f"  💬 Xabarlar: <b>{fmt_num(stats.get('messages_total', 0))}</b>\n"
        f"  🎤 Ovozli: <b>{fmt_num(stats.get('voice_total', 0))}</b>\n"
        f"\n🧠 <b>Quiz:</b>\n"
        f"  🎮 O'yinlar: <b>{fmt_num(quiz_played)}</b>\n"
        f"  ✅ To'g'ri: <b>{fmt_num(quiz_correct)}</b>\n"
        f"  📊 Aniqlik: <b>{accuracy}</b>\n"
        f"  🧩 IQ: <b>{stats.get('iq_score', 0) or '—'}</b>\n"
        f"\n🔥 <b>Streak:</b> {stats.get('streak_days', 0)} kun\n"
        f"📚 Darslar: <b>{fmt_num(stats.get('lessons_total', 0))}</b>\n"
    )

    # Wallet info
    points = wallet.get("points", 0)
    referrals = wallet.get("total_referrals", 0)
    if points > 0 or referrals > 0:
        text += (
            f"\n💰 <b>Hamyon:</b>\n"
            f"  🎯 Ballar: <b>{fmt_num(int(points))}</b>\n"
            f"  👥 Referrallar: <b>{referrals}</b>\n"
        )

    # Today's usage
    text += (
        f"\n📅 <b>Bugun:</b>\n"
        f"  ✅ {usage.get('checks', 0)}/{plan.get('checks_per_day', 12)} tekshiruv\n"
        f"  🧠 {usage.get('quiz', 0)}/{plan.get('quiz_per_day', 5)} quiz\n"
        f"  💬 {usage.get('ai_messages', 0)}/{plan.get('ai_messages_day', 20)} AI xabar\n"
        f"  🔊 {usage.get('pron_audio', 0)}/{plan.get('pron_audio_per_day', 5)} talaffuz\n"
    )

    await safe_reply(message, text)


@router.message(Command("bonus"))
async def cmd_bonus(message: Message, db_user: dict | None = None):
    """Show referral wallet and invite link."""
    if not db_user:
        return
    await send_bonus_panel(message, db_user)


@router.message(Command("clear"))
async def cmd_clear(message: Message, db_user: dict | None = None):
    """Clear chat history."""
    if not db_user:
        return

    from src.database.dao.history_dao import clear_history
    await clear_history(db_user["user_id"])
    await safe_reply(message, "🗑 <b>Suhbat tarixi tozalandi!</b>")

@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message, db_user: dict | None = None):
    """Show global leaderboard based on XP."""
    from src.database.connection import get_db
    db = await get_db()
    
    # Get top 10 by total_xp
    cursor = await db.execute('''
        SELECT u.first_name, u.username, x.total_xp, x.current_level 
        FROM user_xp x
        JOIN users u ON x.user_id = u.user_id
        WHERE x.total_xp > 0
        ORDER BY x.total_xp DESC
        LIMIT 10
    ''')
    leaders = await cursor.fetchall()
    
    if not leaders:
        await safe_reply(message, "🏆 <b>Reyting</b>\n\nHali reytingda hech kim yo'q. Birinchi bo'ling!")
        return
        
    text = "🏆 <b>Global XP Reytingi (Top 10)</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, r in enumerate(leaders):
        name = escape_html(r["first_name"] or r["username"] or "Student")
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} <b>{name}</b> (Lvl {r['current_level']}) — {fmt_num(r['total_xp'])} XP\n"
        
    text += "\n<i>XP ishlash uchun dars qiling, quiz yeching va Pomodoro dan foydalaning!</i>"
    await safe_reply(message, text)
