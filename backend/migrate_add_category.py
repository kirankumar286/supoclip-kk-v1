"""One-shot migration: add duration_category column to generated_clips."""
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
            text("ALTER TABLE generated_clips ADD COLUMN IF NOT EXISTS duration_category VARCHAR(20)")
        )
    print("Migration successful: duration_category column added")
    await engine.dispose()

asyncio.run(main())
