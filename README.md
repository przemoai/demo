# Cart POC — Scalable Stateful REST API with Replica Synchronization

A minimal e-commerce backend (products, carts, orders) that proves two
stateless API replicas can share and synchronize cart state through
Valkey, while orders are durably persisted in MongoDB.

## Architecture

```
                 ┌────────────┐        ┌────────────┐
   client ──────▶│  Replica 1 │        │  Replica 2 │◀────── client
                 └─────┬──────┘        └──────┬─────┘
                       │                       │
                       │      read/write       │
                       ▼                       ▼
                 ┌──────────────────────────────────┐
                 │              Valkey               │
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

Cart state (`cart:{user_id}`, a Valkey hash of `product_id → quantity`)
lives **only** in Valkey. Every cart read (`GET /cart/{user_id}`) and
write (add/remove item) goes directly to Valkey on every request. This
means consistency across replicas is guaranteed by construction: there
is nothing to go stale, because neither replica ever caches cart data
locally. A request to Replica 2 always sees whatever Replica 1 last
wrote, and vice versa.

### Why Valkey Pub/Sub is used

On top of that shared-state read/write path, every cart mutation
(`item_added`, `item_removed`, `cart_cleared`) is published to a Valkey
Pub/Sub channel, `cart-events`. Each replica subscribes to that channel
on startup and logs every event it receives — including events published
by *itself* and by the *other* replica. This makes the cross-replica
awareness required by this POC directly observable in
`docker compose logs`: you can watch Replica 2's logs and see it react
to a change made through Replica 1 in real time.

Pub/Sub was chosen (over Kafka/RabbitMQ) because it is already provided
by the same Valkey instance used for state, requires no extra
infrastructure, and is a natural fit for a "notify other replicas of a
change" signal that doesn't need durability or replay — the state itself
is durable in Valkey; the channel is purely a live notification of that
state changing.

### How MongoDB is used

`POST /orders` reads the current cart from Valkey, builds an order
document (items, quantities, prices, total, timestamp), inserts it into
the `orders` collection in MongoDB, and then clears the cart in Valkey
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
  valkey_client.py   Valkey connection lifecycle
  mongo_client.py    MongoDB connection lifecycle
  events.py          Cart event publish + cross-replica subscriber task
  product_service.py Static product catalog
  cart_service.py    Cart business logic (Valkey-backed)
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

This starts Valkey, MongoDB, and two API replicas:

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
(both replicas, real Valkey, real MongoDB) rather than mocking the
architecture away. With the stack running:

```bash
docker compose up -d
uv sync
uv run pytest
```

`tests/test_replica_sync.py` is the key module: it proves a cart change
made through Replica 1 is visible through Replica 2 (and vice versa),
that order creation persists the cart contents added on a different
replica, and that the Valkey Pub/Sub event is actually published on
`cart-events`. `tests/test_libvalkey_parser.py` is a unit test (no
Docker stack required) that confirms the native `libvalkey` response
parser is actually importable, not just declared as a dependency.

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
| `REDIS_URL`          | Valkey connection URL (name kept for backward compatibility — see note below) |
| `MONGODB_URL`        | MongoDB connection URL                        |
| `MONGODB_DATABASE`   | MongoDB database name                         |
| `REPLICA_ID`         | Identifies this replica in logs and responses |
| `LOG_LEVEL`          | Python logging level                          |

The same container image is used for both replicas in
`docker-compose.yml`; only `REPLICA_ID` differs between them.

## Dependencies

| Concern                  | Library                                      |
|---------------------------|----------------------------------------------|
| HTTP API                  | FastAPI                                      |
| Schemas / settings        | Pydantic, pydantic-settings                  |
| Shared state / Pub/Sub    | `valkey[libvalkey]` (valkey-py + libvalkey)  |
| Orders persistence        | `pymongo` (native async driver, `AsyncMongoClient`) |
| Server                    | Uvicorn                                      |

### Why Valkey instead of Redis

This project uses [Valkey](https://valkey.io), the Linux
Foundation-governed, BSD-licensed fork of Redis, via the official
[`valkey-py`](https://github.com/valkey-io/valkey-py) client with the
[`libvalkey`](https://github.com/valkey-io/libvalkey-py) native response
parser (`valkey[libvalkey]` — auto-enabled whenever it's importable, no
code change required). The local stack runs
`valkey/valkey:9.1.2-alpine` (the latest stable Valkey 9.x release at
the time of writing), pinned explicitly rather than `:latest` for
reproducible builds.

`valkey-py` is a fork of `redis-py` with (for the commands this project
uses — hashes, `DEL`, `PUBLISH`/pub-sub) an identical async API; the only
code change was `redis.asyncio.Redis` → `valkey.asyncio.Valkey` and the
module rename `app/redis_client.py` → `app/valkey_client.py`. The
`REDIS_URL` environment variable name and its `redis://` URL scheme are
both kept unchanged: `valkey-py`'s `from_url()` accepts `redis://`,
`rediss://`, `valkey://`, and `valkeys://` natively, so nothing
downstream (`.env` files, deployment configs) needs to change on
account of the rename alone. This project has no pipelines/transactions,
Lua scripts, or Cluster/Sentinel usage, so those parts of the
redis-py → valkey-py surface aren't exercised here.

### Why `pymongo`'s native async driver instead of Motor

MongoDB orders use `pymongo.AsyncMongoClient` (PyMongo's native asyncio
driver, stable since PyMongo 4.9) rather than Motor — Motor is now a
thin wrapper around the same PyMongo internals and has been deprecated
in its favor.

## Deliberate scope limits

Per the POC's engineering constraints, this deliberately does **not**
include Kubernetes, Kafka/RabbitMQ, Celery, a service mesh, API gateway,
event sourcing/CQRS, distributed transactions, or additional caching
layers. Valkey Pub/Sub plus direct Valkey reads are sufficient to
demonstrate the one architectural idea this POC targets: stateless
replicas sharing state through Valkey, with durable orders in MongoDB.
