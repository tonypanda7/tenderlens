"""Create all database tables from ORM models."""
import asyncio
from app.shared.database import engine, Base
from app.shared import models  # noqa: F401 — ensures all models are registered

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created successfully!")

asyncio.run(create_tables())
