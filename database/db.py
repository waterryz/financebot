import asyncpg
from core.config import config

async def create_pool():
    return await asyncpg.create_pool(dsn=config.DB_URL)
