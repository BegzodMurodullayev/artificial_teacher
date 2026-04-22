import asyncio
from aiogram import Bot

async def main():
    bot = Bot(token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    try:
        await bot.send_message(chat_id=123, text="test", disable_web_page_preview=True)
    except Exception as e:
        print(repr(e))

asyncio.run(main())
