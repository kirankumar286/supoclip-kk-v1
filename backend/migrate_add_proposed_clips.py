"""One-shot migration: add proposed_clips column to tasks."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = (
    "postgresql+asyncpg://neondb_owner:npg_3ZaVyG4ntDMl"
    "@ep-royal-lake-az8k60cz.c-3.ap-southeast-1.aws.neon.tech/neondb"
)

async def main():
    engine = create_async_engine(DB_URL, connect_args={"ssl": True})
    async with engine.begin() as conn:
        await conn.execute(
            text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS proposed_clips TEXT")
        )
    print("Migration successful: proposed_clips column added to tasks")
    await engine.dispose()

asyncio.run(main())
