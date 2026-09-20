"""Management CLI.

Usage:
    uv run python -m app.manage create-user --email a@b.com --password secret [--role admin]
"""

import argparse
import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import SessionLocal
from app.models.user import User, UserCredential


async def _create_user(email: str, password: str, role: str) -> None:
    async with SessionLocal() as session:
        existing = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            print(f"user already exists: {email} ({existing.id})")
            return
        user = User(email=email, role=role)
        session.add(user)
        await session.flush()
        session.add(UserCredential(user_id=user.id, password_hash=hash_password(password)))
        await session.commit()
        print(f"created user {user.id} <{email}> role={role}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.manage")
    sub = parser.add_subparsers(dest="command", required=True)
    cu = sub.add_parser("create-user")
    cu.add_argument("--email", required=True)
    cu.add_argument("--password", required=True)
    cu.add_argument("--role", default="user", choices=["user", "admin"])
    args = parser.parse_args()

    if args.command == "create-user":
        asyncio.run(_create_user(args.email, args.password, args.role))


if __name__ == "__main__":
    main()
