from aiogram import Bot, Dispatcher
from bot.handlers import register_handlers

def create_app(token):
    bot = Bot(token=token)
    dp = Dispatcher()
    register_handlers(dp)
    return bot, dp
