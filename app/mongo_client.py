"""MongoDB connection lifecycle. MongoDB is the source of truth for orders.

Uses PyMongo's native async driver (`AsyncMongoClient`, available since
PyMongo 4.9) rather than Motor: Motor is now a thin wrapper around the
same PyMongo internals and has been deprecated by MongoDB in favor of
this driver, so depending on it directly avoids an extra dependency for
no added capability.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.config import get_settings


@asynccontextmanager
async def mongo_lifespan() -> AsyncIterator[AsyncDatabase]:
    settings = get_settings()
    client: AsyncMongoClient = AsyncMongoClient(settings.mongodb_url)
    try:
        await client.admin.command("ping")
        db = client[settings.mongodb_database]
        await db.orders.create_index("user_id")
        yield db
    finally:
        await client.close()
