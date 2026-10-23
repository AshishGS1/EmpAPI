"""Minting the RS256 tokens the MCP server verifies.

One fresh token per MCP call (signing costs under a millisecond, so there is nothing
worth caching), carrying:

    sub    the API user, which the MCP server logs as ``caller=``
    scope  only what this call needs (least privilege), plus salary:read if the user has it
    jti    this API request's id, which the MCP server logs as ``jti=``
    exp    short-lived (AUTH_TOKEN_TTL_SECONDS, default 5 minutes)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from joserfc import jwt
from joserfc.jwk import RSAKey

from empapi.config import Settings
from empapi.exceptions import ConfigurationError
from empapi.mcp.consts import JWT_ALGORITHM, MIN_RSA_KEY_BITS, BOOTSTRAP_SUBJECT


def load_private_key(path: str) -> RSAKey:
    """Read and validate the signing key; raises ConfigurationError if unusable."""
    try:
        pem = Path(path).read_bytes()
    except OSError as exc:
        raise ConfigurationError(
            f"Cannot read AUTH_PRIVATE_KEY_PATH ({path})",
            details={"path": path, "reason": exc.strerror},
        ) from exc
    try:
        key = serialization.load_pem_private_key(pem, password=None)
    except (ValueError, TypeError, UnsupportedAlgorithm) as exc:
        raise ConfigurationError(
            "AUTH_PRIVATE_KEY_PATH must point to an unencrypted PEM RSA private key",
            details={"path": path},
        ) from exc
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ConfigurationError("AUTH_PRIVATE_KEY_PATH must be an RSA key", details={"path": path})
    if key.key_size < MIN_RSA_KEY_BITS:
        raise ConfigurationError(
            f"RSA key must be at least {MIN_RSA_KEY_BITS} bits",
            details={"path": path, "key_bits": key.key_size},
        )
    return RSAKey.import_key(pem)


class TokenMinter:
    def __init__(self, key: RSAKey, issuer: str, audience: str, ttl_seconds: int) -> None:
        self._key = key
        self._issuer = issuer
        self._audience = audience
        self._ttl = ttl_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> "TokenMinter":
        return cls(
            load_private_key(settings.auth_private_key_path),
            settings.auth_issuer,
            settings.auth_audience,
            settings.auth_token_ttl_seconds,
        )

    def mint(self, *, sub: str, scopes: Iterable[str], jti: str) -> str:
        now = int(time.time())
        claims = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": sub,
            "scope": " ".join(sorted(scopes)),
            "iat": now,
            "exp": now + self._ttl,
            "jti": jti,
        }
        return jwt.encode({"alg": JWT_ALGORITHM, "typ": "JWT"}, claims, self._key)

    def mint_bootstrap(self) -> str:
        """For requests that belong to no user: the MCP handshake and health pings.
        No scopes, so it cannot call a tool."""
        return self.mint(sub=BOOTSTRAP_SUBJECT, scopes=(), jti="bootstrap")
