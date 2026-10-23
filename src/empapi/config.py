"""Environment-driven configuration (pydantic-settings)."""



from functools import lru_cache

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from empapi.exceptions import ConfigurationError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # API
    api_host: str = "127.0.0.1"
    api_port: int = Field(8000, ge=1, le=65535)

    # MCP server
    mcp_url: str = "http://127.0.0.1:8001/mcp"
    mcp_connect_timeout_seconds: float = Field(3, gt=0)
    mcp_call_timeout_seconds: float = Field(10, gt=0)

    # Token signing (RS256). The private key never leaves this service; the MCP server
    # only holds the public half. Issuer and audience must equal the MCP server's.
    auth_private_key_path: str
    auth_issuer: str
    auth_audience: str
    auth_token_ttl_seconds: int = Field(300, ge=30, le=3600)

    # Oracle (the api_users table)
    oracle_user: str
    oracle_password: SecretStr
    oracle_dsn: str
    oracle_pool_timeout_seconds: int = Field(10, ge=1)

    # API keys: how long a looked-up key is cached (a revoked key lives this long)
    user_cache_ttl_seconds: float = Field(30, ge=0)

    # Logging
    log_level: str = "INFO"
    log_json: bool = True


@lru_cache
def get_settings() -> Settings:
    """Load settings once; turn validation failures into a ConfigurationError."""
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        problems = [
            {
                "field": ".".join(str(p) for p in err["loc"]) or "settings",
                "problem": err["msg"],
            }
            for err in exc.errors()
        ]
        raise ConfigurationError(
            "Invalid or missing configuration", details={"errors": problems}
        ) from exc
