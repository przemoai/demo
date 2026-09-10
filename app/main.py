import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import EmptyCartError, ProductNotFoundError
from app.events import start_subscriber_task
from app.logging_config import configure_logging
from app.mongo_client import mongo_lifespan
from app.redis_client import redis_lifespan
from app.routers import cart, orders, products

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    async with redis_lifespan() as redis, mongo_lifespan() as mongo_db:
        app.state.redis = redis
        app.state.mongo_db = mongo_db
        subscriber_task = start_subscriber_task(redis)
        logger.info("replica '%s' started and subscribed to cart events", settings.replica_id)
        try:
            yield
        finally:
            subscriber_task.cancel()
            logger.info("replica '%s' shutting down", settings.replica_id)


app = FastAPI(title="Cart POC", lifespan=lifespan)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)


@app.middleware("http")
async def add_replica_header(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers["X-Replica-Id"] = get_settings().replica_id
    return response


@app.exception_handler(ProductNotFoundError)
async def product_not_found_handler(
    _request: Request, exc: ProductNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(EmptyCartError)
async def empty_cart_handler(_request: Request, exc: EmptyCartError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "replica_id": get_settings().replica_id}
