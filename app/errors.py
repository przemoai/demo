"""Domain exceptions. Mapped to HTTP responses in app.main."""


class ProductNotFoundError(Exception):
    def __init__(self, product_id: str) -> None:
        self.product_id = product_id
        super().__init__(f"Product '{product_id}' not found")


class EmptyCartError(Exception):
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(f"Cart for user '{user_id}' is empty")
