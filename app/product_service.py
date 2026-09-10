"""Product catalog.

Products are static reference data for this POC (no create/update/delete
requirement was specified), so they're kept as an in-memory catalog rather
than a database collection — this keeps the POC's only two stateful
concerns, cart and orders, focused on the architecture being demonstrated.
"""

from app.errors import ProductNotFoundError
from app.models import Product

_CATALOG: dict[str, Product] = {
    p.id: p
    for p in (
        Product(
            id="p1", name="Mechanical Keyboard", price=89.99, description="Tactile brown switches"
        ),
        Product(id="p2", name="Wireless Mouse", price=29.99, description="Ergonomic, 2.4GHz"),
        Product(id="p3", name="27-inch Monitor", price=249.99, description="1440p IPS display"),
        Product(id="p4", name="USB-C Hub", price=39.99, description="7-in-1 dock"),
        Product(id="p5", name="Laptop Stand", price=24.99, description="Aluminum, adjustable"),
    )
}


def list_products() -> list[Product]:
    return list(_CATALOG.values())


def get_product(product_id: str) -> Product:
    product = _CATALOG.get(product_id)
    if product is None:
        raise ProductNotFoundError(product_id)
    return product
