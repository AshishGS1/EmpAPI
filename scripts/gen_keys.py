"""Generate the RSA key pair for signing MCP tokens.

    python scripts/gen_keys.py [--dir keys] [--force]

keys/private.pem stays with THIS service (AUTH_PRIVATE_KEY_PATH, chmod 600, never in
git). Copy keys/public.pem to the MCP server (its AUTH_PUBLIC_KEY_PATH). In production
keep the private key in a secret store instead of on disk.
"""



import argparse
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dir", default="keys")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    out = Path(args.dir)
    private_path, public_path = out / "private.pem", out / "public.pem"
    if (private_path.exists() or public_path.exists()) and not args.force:
        sys.exit(f"{out}/ already has keys; pass --force to overwrite")
    out.mkdir(parents=True, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    os.chmod(private_path, 0o600)
    public_path.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    print(f"wrote {private_path} (keep secret) and {public_path} (give to the MCP server)")


if __name__ == "__main__":
    main()
