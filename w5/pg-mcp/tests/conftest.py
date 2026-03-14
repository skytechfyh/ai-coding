from __future__ import annotations

import os

import asyncpg
import pytest


@pytest.fixture(scope="session")
def pg_dsn() -> str:
    dsn = os.environ.get("TEST_PG_DSN")
    if not dsn:
        pytest.skip("TEST_PG_DSN not set — skipping integration tests")
    return dsn


@pytest.fixture(scope="session")
async def pg_pool(pg_dsn: str):
    pool = await asyncpg.create_pool(
        pg_dsn,
        server_settings={"default_transaction_read_only": "true"},
    )
    yield pool
    await pool.close()
