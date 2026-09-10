import pytest
from httpx2 import AsyncClient


@pytest.mark.asyncio
async def test_list_products(replica1: AsyncClient) -> None:
    response = await replica1.get("/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) > 0
    assert {"id", "name", "price", "description"} <= products[0].keys()


@pytest.mark.asyncio
async def test_get_product(replica1: AsyncClient) -> None:
    response = await replica1.get("/products/p1")
    assert response.status_code == 200
    assert response.json()["id"] == "p1"


@pytest.mark.asyncio
async def test_get_unknown_product_returns_404(replica1: AsyncClient) -> None:
    response = await replica1.get("/products/does-not-exist")
    assert response.status_code == 404
