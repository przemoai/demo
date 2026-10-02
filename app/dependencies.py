from fastapi import Request
from pymongo.asynchronous.database import AsyncDatabase
from valkey.asyncio import Valkey


def get_valkey(request: Request) -> Valkey:
    return request.app.state.valkey


def get_mongo_db(request: Request) -> AsyncDatabase:
    return request.app.state.mongo_db
