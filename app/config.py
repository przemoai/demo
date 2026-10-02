"""Environment-based application configuration.

All runtime configuration is read from the environment (optionally via a
local .env file). Nothing here is hardcoded, and the same container image
can be deployed to any environment by changing environment variables only.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Field/env-var name kept as `redis_url`/`REDIS_URL` for backward
    # compatibility — valkey-py accepts `redis://` URLs natively, and this
    # points at the Valkey instance in docker-compose.yml.
    redis_url: str = Field(..., description="Valkey (Redis-protocol-compatible) connection URL")
    mongodb_url: str = Field(..., description="MongoDB connection URL")
    mongodb_database: str = Field(..., description="MongoDB database name")

    replica_id: str = Field(default="unknown", description="Identifier for this replica")
    log_level: str = Field(default="INFO")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
