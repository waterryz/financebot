import asyncio
import sys
import os

# Добавляем путь к webapp/, чтобы работал import webapp.db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from webapp.db import save_telegram_id, get_user_id

TOKEN = "8332054798:AAGLpizBXxlQ2A4ByeE-L-aV5Ginm3mHkPw"
WEBAPP_URL = "https://overmournful-extrapolatory-maya.ngrok-free.dev/"


bot = Bot(token=TOKEN)
dp = Dispatcher()


# ============================
#         /start
# ============================
@dp.message(Command("start"))
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])

    await message.answer(
        "👋 Привет! Нажми кнопку, чтобы открыть приложение.\n"
        "Чтобы связать аккаунт сайта и бота — используй команду:\n\n"
        "/bind <логин>",
        reply_markup=kb
    )


# ============================
#         /bind
# ============================
@dp.message(Command("bind"))
async def bind(message: types.Message):
    text = message.text.split()

    if len(text) < 2:
        await message.answer("❗ Формат: /bind ЛОГИН")
        return

    username = text[1].strip()

    user_id = get_user_id(username)
    if not user_id:
        await message.answer("❌ Пользователь с таким логином не найден!")
        return

    save_telegram_id(user_id, message.from_user.id)

    await message.answer(
        f"✅ Аккаунт <b>{username}</b> успешно привязан!\n"
        "Теперь я смогу отправлять тебе напоминания.",
        parse_mode="HTML"
    )


# ============================
#         START BOT
# ============================
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
