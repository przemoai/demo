import pytest
from httpx2 import AsyncClient


@pytest.mark.asyncio
async def test_empty_cart(replica1: AsyncClient, user_id: str) -> None:
    response = await replica1.get(f"/cart/{user_id}")
    assert response.status_code == 200
    assert response.json() == {"user_id": user_id, "items": [], "total": 0.0}


@pytest.mark.asyncio
async def test_add_item_to_cart(replica1: AsyncClient, user_id: str) -> None:
    response = await replica1.post(
        f"/cart/{user_id}/items", json={"product_id": "p1", "quantity": 2}
    )
    assert response.status_code == 200
    cart = response.json()
    assert cart["items"] == [
        {
            "product_id": "p1",
            "name": "Mechanical Keyboard",
            "price": 89.99,
            "quantity": 2,
            "subtotal": 179.98,
        }
    ]
    assert cart["total"] == pytest.approx(179.98)


@pytest.mark.asyncio
async def test_add_unknown_product_returns_404(replica1: AsyncClient, user_id: str) -> None:
    response = await replica1.post(
        f"/cart/{user_id}/items", json={"product_id": "does-not-exist", "quantity": 1}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_item_from_cart(replica1: AsyncClient, user_id: str) -> None:
    await replica1.post(f"/cart/{user_id}/items", json={"product_id": "p2", "quantity": 1})

    response = await replica1.delete(f"/cart/{user_id}/items/p2")
    assert response.status_code == 200
    assert response.json()["items"] == []
