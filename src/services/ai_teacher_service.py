"""
AI Teacher Service.
Handles intent detection, smart routing, and contextual Q&A based on the bot's documentation.
"""

import logging

from src.services import ai_service
from src.database.dao.history_dao import get_history

logger = logging.getLogger(__name__)

# Fallback values
DEFAULT_INTENT = "CORRECTION"

BOT_DOCUMENTATION = """
# Artificial Teacher - System Documentation
You are "Artificial Teacher", an English tutor built as a Telegram bot.

## Core Features
1. **Grammar Correction**: If users type in English, you analyze and correct their grammar automatically.
2. **Translation**: If users type in Uzbek/Russian, you translate it to natural English.
3. **Pronunciation**: Users can ask for pronunciation (by replying #p), and you provide IPA and audio (via TopMediai TTS).
4. **Quiz**: Users can play a multiple-choice English grammar/vocabulary quiz.
5. **WebApp / Dashboard**: Users can track their progress, view leveling, and use a Pomodoro timer via the Telegram WebApp button.

## Subscription Plans
- **Free**: 12 checks/day, 5 quiz/day, 20 AI messages/day
- **Standard (29,000 UZS/month)**: 40 checks/day, 15 quiz/day, Voice messages enabled
- **Pro (59,000 UZS/month)**: 120 checks/day, 40 quiz/day, IQ tests enabled
- **Premium (99,000 UZS/month)**: Unlimited almost everything, Group bot enabled

## Commands
- `/start` - Start the bot, show welcome menu
- `/profile` or `/mystats` - Show global XP, rank, level, and limits
- `/quiz` - Start a quiz session in chat
- `/subscribe` or `/plans` - Show subscription plans and purchase link
- `/teacher` - Force 'Teacher' mode (Q&A mode)
- `/correct` - Force 'Grammar Correction' mode
- `/translate` - Force 'Translation' mode
- `/tech` - Force 'Technical' mode
- `/cancel` - Reset mode to Auto

Always answer users' questions about these features politely and concisely. If they ask about pricing, clearly quote the UZS amounts. 
"""

async def get_intent(text: str, user_id: int = 0) -> str:
    """
    Classify the user's intent to route them to the correct handler.
    Returns one of: TEACHER, CORRECTION, TRANSLATION, TECHNICAL, PRONUNCIATION
    """
    result = await ai_service.ask_json(text, mode="intent", user_id=user_id)
    if not result or "intent" not in result:
        return DEFAULT_INTENT
        
    intent = str(result["intent"]).upper()
    valid_intents = {"TEACHER", "CORRECTION", "TRANSLATION", "TECHNICAL", "PRONUNCIATION"}
    
    if intent in valid_intents:
        return intent
    return DEFAULT_INTENT


async def ask_teacher(text: str, user_id: int) -> str:
    """
    Provide an answer in Teacher mode based on Bot Documentation and Conversation History.
    """
    # Get last 5 messages from database
    raw_history = await get_history(user_id, limit=5)
    
    # Format history for openrouter API
    history = []
    # Inject Bot Documentation into the first system message explicitly along with history
    history.append({
        "role": "system", 
        "content": BOT_DOCUMENTATION
    })
    
    for row in reversed(raw_history):
        # Convert DB history format to API format
        # row: id, user_id, role, content, created_at
        role = row["role"]
        content = row["content"]
        history.append({"role": role, "content": content})
        
    response = await ai_service.ask_ai(
        text=text,
        mode="teacher",
        user_id=user_id,
        history=history,
        temperature=0.5
    )
    
    return response
