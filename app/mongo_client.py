"""MongoDB connection lifecycle. MongoDB is the source of truth for orders."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings


@asynccontextmanager
async def mongo_lifespan() -> AsyncIterator[AsyncIOMotorDatabase]:
    settings = get_settings()
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongodb_url)
    try:
        await client.admin.command("ping")
        db = client[settings.mongodb_database]
        await db.orders.create_index("user_id")
        yield db
    finally:
        client.close()
