from fastapi import APIRouter, Depends
from valkey.asyncio import Valkey

from app import cart_service
from app.dependencies import get_valkey
from app.models import AddCartItemRequest, Cart

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("/{user_id}", response_model=Cart)
async def get_cart(user_id: str, valkey: Valkey = Depends(get_valkey)) -> Cart:
    return await cart_service.get_cart(valkey, user_id)


@router.post("/{user_id}/items", response_model=Cart)
async def add_item(
    user_id: str, body: AddCartItemRequest, valkey: Valkey = Depends(get_valkey)
) -> Cart:
    return await cart_service.add_item(valkey, user_id, body.product_id, body.quantity)


@router.delete("/{user_id}/items/{product_id}", response_model=Cart)
async def remove_item(user_id: str, product_id: str, valkey: Valkey = Depends(get_valkey)) -> Cart:
    return await cart_service.remove_item(valkey, user_id, product_id)
