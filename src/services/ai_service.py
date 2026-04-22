"""
AI Service — OpenRouter API client with concurrency control and retry logic.
This is the single point of contact for all AI interactions.
"""

import asyncio
import json
import logging
import re
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

# Concurrency limiter
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.AI_CONCURRENCY)
    return _semaphore


# ── System Prompts ──────────────────────────────────────────

SYSTEM_PROMPTS = {
    "check": """You are an English grammar expert and teacher.
Analyze the text for grammatical errors.
Return JSON: {"level": "A1-C2", "original": "text", "analysis": [{"error": "...", "correction": "...", "explanation": "..."}], "corrected": "full corrected text", "summary": "overall summary"}
If no errors found, return empty analysis array and say "No errors found" in summary.
Respond ONLY with JSON, no markdown.""",

    "translate_uz_en": """You are a professional UZ→EN translator.
Translate the Uzbek text to natural English.
Return JSON: {"original": "uzbek text", "translation": "english text", "notes": "any relevant notes about the translation"}
Respond ONLY with JSON.""",

    "translate_en_uz": """You are a professional EN→UZ translator.
Translate the English text to natural Uzbek.
Return JSON: {"original": "english text", "translation": "uzbek text", "notes": "translation notes"}
Respond ONLY with JSON.""",

    "translate_ru_en": """You are a professional RU→EN translator.
Translate the Russian text to natural English.
Return JSON: {"original": "russian text", "translation": "english text", "notes": "any relevant notes about the translation"}
Respond ONLY with JSON.""",

    "translate_en_ru": """You are a professional EN→RU translator.
Translate the English text to natural Russian.
Return JSON: {"original": "english text", "translation": "russian text", "notes": "translation notes"}
Respond ONLY with JSON.""",

    "pronunciation": """You are an English pronunciation expert.
Provide a detailed pronunciation guide for the given word/phrase.
Return JSON: {"word": "...", "ipa_us": "/.../ (US)", "ipa_uk": "/.../ (UK)", "syllables": "syl-la-bles", "tips": ["tip1", "tip2"], "example_sentences": ["sentence1", "sentence2"], "common_mistakes": ["mistake1"]}
Respond ONLY with JSON.""",

    "lesson": """You are an English teacher creating an interactive lesson.
Create a comprehensive lesson on the given topic for the specified level.
Include: title, objectives, vocabulary (word + definition + example), grammar points, exercises, and a summary.
Return JSON format.""",

    "grammar_rule": """You are an English grammar expert.
Explain the given grammar topic clearly with examples.
Use the student's level to adjust complexity.
Include: rule explanation, examples (correct and incorrect), common mistakes, and practice exercises.
Return structured text.""",

    "quiz_generate": """You are a quiz master for English learners.
Generate a multiple-choice question for the given level.
Return JSON: {"question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "answer": "A/B/C/D", "explanation": "...", "difficulty": 0.0-1.0, "key": "unique_short_key"}
The question should test grammar, vocabulary, or comprehension.
Respond ONLY with valid JSON.""",

    "iq_question": """Generate a logical reasoning question (IQ-style).
Return JSON: {"question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "answer": "A/B/C/D", "explanation": "...", "difficulty": 0.0-1.0, "key": "unique_short_key"}
Questions should test: pattern recognition, number sequences, word analogies, or logical deduction.
Respond ONLY with valid JSON.""",

    "daily_word": """You are a vocabulary teacher.
Generate a random English word suitable for intermediate learners.
Return JSON: {"word": "...", "part_of_speech": "noun/verb/adj/...", "definition": "...", "example": "example sentence", "synonyms": ["..."], "uzbek": "uzbek translation"}
Choose an interesting, useful word. Respond ONLY with JSON.""",

    "word_card": """You are an English vocabulary expert.
Generate a beautiful word card for the provided word.
Return JSON: {"word": "...", "translation": "uzbek translation", "ipa": "pronunciation", "part_of_speech": "noun/verb/adj/...", "definition": "english definition", "example": "english example sentence", "example_translation": "uzbek translation of example"}
Respond ONLY with valid JSON.""",

    "bot": """You are Artificial Teacher, a friendly AI English tutor.
Help the user learn English. Be encouraging and educational.
If they write in Uzbek, respond in Uzbek but teach English concepts.
If they write in English, help them improve.
Keep responses concise and helpful.""",

    "level_estimate": """Estimate the English proficiency level (A1, A2, B1, B2, C1, C2) of the text author.
Consider: vocabulary range, grammar complexity, sentence structure, and errors.
Return ONLY the level as a string, e.g. "B1".""",

    "intent": """You are an intent router for Artificial Teacher.
Analyze the user's input and classify its intent into ONE of these categories:
- TEACHER: User asks about the bot, how to use it, subscriptions, prices, or general chat.
- CORRECTION: User speaks English and wants grammar check or improvement.
- TRANSLATION: User speaks Uzbek/Russian and wants translation to English.
- TECHNICAL: User sends code, long text, formatting requests, or complex explanations.
- PRONUNCIATION: User asks how to pronounce a word.
Return JSON: {"intent": "TEACHER/CORRECTION/TRANSLATION/TECHNICAL/PRONUNCIATION"}""",

    "teacher": """You are Artificial Teacher, an advanced AI English tutor.
Use the provided system documentation to answer questions about your features, subscription plans, and commands.
Be helpful, concise, and friendly. Answer in the language the user asked (usually Uzbek or English).
Respond in Markdown format.""",
}


async def ask_ai(
    text: str,
    mode: str = "bot",
    user_id: int = 0,
    level: str = "A1",
    history: list[dict] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """Send a prompt to OpenRouter and get a text response."""
    sem = _get_semaphore()
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["bot"])

    # Inject level into system prompt
    if "{level}" in system_prompt:
        system_prompt = system_prompt.replace("{level}", level)

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history if provided
    if history:
        messages.extend(history[-10:])  # Keep last 10 messages

    messages.append({"role": "user", "content": text})

    async with sem:
        for attempt in range(settings.AI_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT) as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.AI_MODEL,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return content.strip()

            except httpx.TimeoutException:
                logger.warning("AI timeout (attempt %d/%d) for user %s",
                             attempt + 1, settings.AI_MAX_RETRIES + 1, user_id)
                if attempt == settings.AI_MAX_RETRIES:
                    return "⏳ AI javob bermadi. Qayta urinib ko'ring."
                await asyncio.sleep(1 * (attempt + 1))

            except Exception as e:
                logger.exception("AI error (attempt %d): %s", attempt + 1, e)
                if attempt == settings.AI_MAX_RETRIES:
                    return "❌ AI xizmati bilan bog'lanib bo'lmadi."
                await asyncio.sleep(1 * (attempt + 1))

    return "❌ Noma'lum xatolik."


async def ask_json(
    text: str,
    mode: str = "check",
    level: str = "A1",
    user_id: int = 0,
) -> dict | None:
    """Send a prompt and parse the response as JSON."""
    raw = await ask_ai(text, mode=mode, level=level, user_id=user_id, temperature=0.3)

    # Try to extract JSON from response
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in response
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse AI JSON response for mode=%s: %.100s", mode, raw)
    return None
