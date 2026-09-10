"""Pydantic schemas for API requests, responses, and stored documents."""

from datetime import datetime

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str
    name: str
    price: float = Field(gt=0)
    description: str


class AddCartItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(default=1, gt=0)


class CartItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int
    subtotal: float


class Cart(BaseModel):
    user_id: str
    items: list[CartItem]
    total: float


class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int
    subtotal: float


class Order(BaseModel):
    order_id: str
    user_id: str
    items: list[OrderItem]
    total: float
    created_at: datetime


class CreateOrderRequest(BaseModel):
    user_id: str
