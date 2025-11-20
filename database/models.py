async def create_tables(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                name TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
async def add_user(pool, telegram_id: int, name: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, name)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO NOTHING;
        """, telegram_id, name)

async def get_user(pool, telegram_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT * FROM users WHERE telegram_id = $1
        """, telegram_id)


