from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_mongo_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.mongo_db
