"""Integration test fixtures.

These tests exercise the real, Dockerized stack (`docker compose up`) over
HTTP against both replicas, rather than mocking Redis/Mongo away — the
whole point of this POC is the cross-replica behavior, so the tests talk
to it exactly like a real client would.
"""

import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx2 import AsyncClient

REPLICA1_URL = os.environ.get("REPLICA1_URL", "http://localhost:8001")
REPLICA2_URL = os.environ.get("REPLICA2_URL", "http://localhost:8002")


@pytest_asyncio.fixture
async def replica1() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(base_url=REPLICA1_URL, timeout=10.0) as client:
        yield client


@pytest_asyncio.fixture
async def replica2() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(base_url=REPLICA2_URL, timeout=10.0) as client:
        yield client


@pytest.fixture
def user_id() -> str:
    """A fresh user id per test, so tests never share cart state."""
    return f"test-user-{uuid.uuid4().hex[:12]}"
