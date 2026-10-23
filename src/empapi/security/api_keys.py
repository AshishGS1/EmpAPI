"""API key format and hashing.

A key is ``emp_`` plus 32 random bytes (urlsafe base64), shown to its owner once, at
creation. Only its SHA-256 is stored. A plain fast hash is right here (unlike for
passwords): the key is 256 bits of randomness, so there is nothing to brute-force,
and a slow hash would just add latency to every request.
"""



import hashlib
import re
import secrets

KEY_PREFIX = "emp_"

def generate_api_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def key_hint(key: str) -> str:
    """Last four characters, stored so an admin can tell which key is which."""
    return key[-4:]
