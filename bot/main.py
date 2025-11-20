import asyncio
from bot.router import create_app
from core.config import config
from database.db import create_pool
from database.models import create_tables

async def run_bot():
    pool = await create_pool()
    await create_tables(pool)

    bot, dp = create_app(config.BOT_TOKEN)

    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(run_bot())
