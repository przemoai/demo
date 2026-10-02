from fastapi import APIRouter, Depends
from pymongo.asynchronous.database import AsyncDatabase
from valkey.asyncio import Valkey

from app import order_service
from app.dependencies import get_mongo_db, get_valkey
from app.models import CreateOrderRequest, Order

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=Order, status_code=201)
async def create_order(
    body: CreateOrderRequest,
    db: AsyncDatabase = Depends(get_mongo_db),
    valkey: Valkey = Depends(get_valkey),
) -> Order:
    return await order_service.create_order(db, valkey, body.user_id)


@router.get("/{user_id}", response_model=list[Order])
async def list_orders(user_id: str, db: AsyncDatabase = Depends(get_mongo_db)) -> list[Order]:
    return await order_service.list_orders(db, user_id)
