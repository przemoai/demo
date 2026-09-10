# Cart POC — Scalable Stateful REST API with Replica Synchronization

A minimal e-commerce backend (products, carts, orders) that proves two
stateless API replicas can share and synchronize cart state through
Redis, while orders are durably persisted in MongoDB.

## Architecture

```
                 ┌────────────┐        ┌────────────┐
   client ──────▶│  Replica 1 │        │  Replica 2 │◀────── client
                 └─────┬──────┘        └──────┬─────┘
                       │                       │
                       │      read/write       │
                       ▼                       ▼
                 ┌──────────────────────────────────┐
                 │               Redis               │
                 │  cart:{user_id}  (hash, source     │
                 │  of truth for cart state)          │
                 │  "cart-events"  (pub/sub channel)  │
                 └──────────────────┬─────────────────┘
                                     │ publish/subscribe
                       ┌─────────────┴─────────────┐
                       ▼                            ▼
              Replica 1 subscriber          Replica 2 subscriber
              (logs incoming events)        (logs incoming events)

                 ┌────────────────────┐
                 │      MongoDB        │  ← orders (source of truth)
                 └────────────────────┘
```

Both replicas run the identical FastAPI application image and are fully
interchangeable — neither has any in-memory cart state, session
affinity, or local storage.

### How replica synchronization works

Cart state (`cart:{user_id}`, a Redis hash of `product_id → quantity`)
lives **only** in Redis. Every cart read (`GET /cart/{user_id}`) and
write (add/remove item) goes directly to Redis on every request. This
means consistency across replicas is guaranteed by construction: there
is nothing to go stale, because neither replica ever caches cart data
locally. A request to Replica 2 always sees whatever Replica 1 last
wrote, and vice versa.

### Why Redis Pub/Sub is used

On top of that shared-state read/write path, every cart mutation
(`item_added`, `item_removed`, `cart_cleared`) is published to a Redis
Pub/Sub channel, `cart-events`. Each replica subscribes to that channel
on startup and logs every event it receives — including events published
by *itself* and by the *other* replica. This makes the cross-replica
awareness required by this POC directly observable in
`docker compose logs`: you can watch Replica 2's logs and see it react
to a change made through Replica 1 in real time.

Pub/Sub was chosen (over Kafka/RabbitMQ) because it is already provided
by the same Redis instance used for state, requires no extra
infrastructure, and is a natural fit for a "notify other replicas of a
change" signal that doesn't need durability or replay — the state itself
is durable in Redis; the channel is purely a live notification of that
state changing.

### How MongoDB is used

`POST /orders` reads the current cart from Redis, builds an order
document (items, quantities, prices, total, timestamp), inserts it into
the `orders` collection in MongoDB, and then clears the cart in Redis
(itself an event-emitting write, so the clear also propagates to the
other replica). MongoDB is the sole source of truth for orders; carts
are never written to MongoDB.

## Project layout

```
app/
  main.py            FastAPI app, lifespan wiring, exception handling
  config.py          Environment-based settings (pydantic-settings)
  logging_config.py  Structured logging tagged with replica id
  models.py          Pydantic request/response schemas
  errors.py          Domain exceptions
  redis_client.py    Redis connection lifecycle
  mongo_client.py    MongoDB connection lifecycle
  events.py          Cart event publish + cross-replica subscriber task
  product_service.py Static product catalog
  cart_service.py    Cart business logic (Redis-backed)
  order_service.py   Order business logic (Mongo-backed)
  routers/           HTTP layer (products, cart, orders)
tests/               Integration tests against the live Docker stack
```

## Running the stack

Requires Docker and Docker Compose.

```bash
cp .env.example .env   # optional, only needed for non-Docker local runs
docker compose up --build
```

This starts Redis, MongoDB, and two API replicas:

- Replica 1: http://localhost:8001
- Replica 2: http://localhost:8002

Check both are healthy:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
```

## API

| Method | Path                              | Description              |
|--------|------------------------------------|---------------------------|
| GET    | `/products`                        | List products             |
| GET    | `/products/{product_id}`           | Get a product              |
| GET    | `/cart/{user_id}`                  | Get a user's cart          |
| POST   | `/cart/{user_id}/items`            | Add an item to the cart    |
| DELETE | `/cart/{user_id}/items/{product_id}` | Remove an item             |
| POST   | `/orders`                          | Create an order from a cart |
| GET    | `/orders/{user_id}`                | List a user's orders       |

## Demonstrating cross-replica cart sharing

```bash
# Add an item via Replica 1
curl -s -X POST http://localhost:8001/cart/alice/items \
  -H "Content-Type: application/json" \
  -d '{"product_id": "p1", "quantity": 2}' | python -m json.tool

# Read the cart via Replica 2 — same items, no coordination needed
curl -s http://localhost:8002/cart/alice | python -m json.tool

# Create the order via Replica 2
curl -s -X POST http://localhost:8002/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice"}' | python -m json.tool

# Verify via Replica 1 that the cart was cleared and the order exists
curl -s http://localhost:8001/cart/alice | python -m json.tool
curl -s http://localhost:8001/orders/alice | python -m json.tool
```

While running the above, `docker compose logs -f api1 api2` shows each
replica publishing and consuming the corresponding `cart-events` message,
tagged with `[replica=replica-1]` / `[replica=replica-2]`.

## Running the tests

The tests are integration tests that exercise the real Dockerized stack
(both replicas, real Redis, real MongoDB) rather than mocking the
architecture away. With the stack running:

```bash
docker compose up -d
uv sync
uv run pytest
```

`tests/test_replica_sync.py` is the key module: it proves a cart change
made through Replica 1 is visible through Replica 2 (and vice versa),
that order creation persists the cart contents added on a different
replica, and that the Redis Pub/Sub event is actually published on
`cart-events`.

## Type checking & linting

```bash
uv run ty check
uv run ruff check .
uv run ruff format .
```

## Configuration

All configuration is environment-based (see `.env.example`):

| Variable            | Description                                   |
|----------------------|-----------------------------------------------|
| `REDIS_URL`          | Redis connection URL                          |
| `MONGODB_URL`        | MongoDB connection URL                        |
| `MONGODB_DATABASE`   | MongoDB database name                         |
| `REPLICA_ID`         | Identifies this replica in logs and responses |
| `LOG_LEVEL`          | Python logging level                          |

The same container image is used for both replicas in
`docker-compose.yml`; only `REPLICA_ID` differs between them.

## Deliberate scope limits

Per the POC's engineering constraints, this deliberately does **not**
include Kubernetes, Kafka/RabbitMQ, Celery, a service mesh, API gateway,
event sourcing/CQRS, distributed transactions, or additional caching
layers. Redis Pub/Sub plus direct Redis reads are sufficient to
demonstrate the one architectural idea this POC targets: stateless
replicas sharing state through Redis, with durable orders in MongoDB.
