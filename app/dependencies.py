from fastapi import Request
from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_mongo_db(request: Request) -> AsyncDatabase:
    return request.app.state.mongo_db
