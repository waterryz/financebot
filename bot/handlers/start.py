from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from database.models import add_user, get_user
from database.db import create_pool

router = Router()

user_waiting_name = set()


@router.message(Command("start"))
async def start(message: Message):
    pool = await create_pool()
    user = await get_user(pool, message.from_user.id)

    if user:
        await message.answer(f"Ты уже зарегистрирован, {user['name']} 👌")
        return


    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Зарегистрироваться")],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True
    )

    await message.answer("Привет! Ты ещё не зарегистрирован 👋", reply_markup=kb)


@router.message(lambda m: m.text == "Зарегистрироваться")
async def ask_name(message: Message):
    user_waiting_name.add(message.from_user.id)
    await message.answer("Отлично! Напиши своё имя:", reply_markup=None)


@router.message(lambda m: m.text == "Отмена")
async def cancel(message: Message):
    await message.answer("Ок, отменил.", reply_markup=None)


@router.message()
async def process_name(message: Message):
    tg_id = message.from_user.id

    # если он не вводит имя — выходим
    if tg_id not in user_waiting_name:
        return

    pool = await create_pool()


    already = await get_user(pool, tg_id)
    if already:
        user_waiting_name.discard(tg_id)
        await message.answer(f"Ты уже зарегистрирован, {already['name']} 👌")
        return


    name = message.text.strip()
    await add_user(pool, tg_id, name)

    user_waiting_name.discard(tg_id)

    await message.answer(f"Готово, {name}! Ты успешно зарегистрирован 🎉")
