import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_order_from_cart(replica1: AsyncClient, user_id: str) -> None:
    await replica1.post(f"/cart/{user_id}/items", json={"product_id": "p1", "quantity": 1})
    await replica1.post(f"/cart/{user_id}/items", json={"product_id": "p2", "quantity": 3})

    response = await replica1.post("/orders", json={"user_id": user_id})
    assert response.status_code == 201
    order = response.json()
    assert order["user_id"] == user_id
    assert {item["product_id"] for item in order["items"]} == {"p1", "p2"}
    assert order["total"] == pytest.approx(89.99 + 3 * 29.99)

    # Order creation must clear the cart.
    cart_response = await replica1.get(f"/cart/{user_id}")
    assert cart_response.json()["items"] == []


@pytest.mark.asyncio
async def test_create_order_with_empty_cart_fails(replica1: AsyncClient, user_id: str) -> None:
    response = await replica1.post("/orders", json={"user_id": user_id})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_order_is_persisted_and_retrievable(replica1: AsyncClient, user_id: str) -> None:
    await replica1.post(f"/cart/{user_id}/items", json={"product_id": "p3", "quantity": 1})
    create_response = await replica1.post("/orders", json={"user_id": user_id})
    order_id = create_response.json()["order_id"]

    list_response = await replica1.get(f"/orders/{user_id}")
    assert list_response.status_code == 200
    orders = list_response.json()
    assert any(order["order_id"] == order_id for order in orders)
