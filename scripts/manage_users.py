"""Create and manage API users (rows in the api_users table).

    python scripts/manage_users.py create --user-id alice --role hr
    python scripts/manage_users.py list
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from empapi.config import get_settings
from empapi.db.user_store import OracleUserStore
from empapi.exceptions import ApiError
from empapi.security.api_keys import generate_api_key, hash_api_key, key_hint
from empapi.security.scopes import ROLES


async def run(args: argparse.Namespace) -> int:
    store = OracleUserStore(get_settings())
    await store.connect()
    try:
        if args.command == "list":
            users = await store.list_users()
            print(f"{'USER':<24} {'ROLE':<10} {'ACTIVE':<7} KEY ENDS IN")
            for u in users:
                print(f"{u.user_id:<24} {u.role:<10} {str(u.is_active):<7} ...{u.key_hint or ''}")
            return 0

        if args.command == "create":
            key = generate_api_key()
            await store.create_user(args.user_id, args.role, hash_api_key(key), key_hint(key))
            print(key)
            print(f"# {args.command}d {args.user_id}; this key is shown only once", file=sys.stderr)
            return 0

        active = args.command == "enable"
        if not await store.set_active(args.user_id, active):
            print(f"No such user: {args.user_id}", file=sys.stderr)
            return 1
        print(f"{args.user_id} is now {'enabled' if active else 'disabled'}", file=sys.stderr)
        return 0
    finally:
        await store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    create = commands.add_parser("create")
    create.add_argument("--user-id", required=True)
    create.add_argument("--role", required=True, choices=ROLES)
    for name in ("disable", "enable"):
        commands.add_parser(name).add_argument("--user-id", required=True)
    args = parser.parse_args()
    try:
        sys.exit(asyncio.run(run(args)))
    except ApiError as exc:
        sys.exit(f"[{exc.code}] {exc.message}")


if __name__ == "__main__":
    main()
