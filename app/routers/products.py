from fastapi import APIRouter

from app import product_service
from app.models import Product

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[Product])
async def list_products() -> list[Product]:
    return product_service.list_products()


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: str) -> Product:
    return product_service.get_product(product_id)
