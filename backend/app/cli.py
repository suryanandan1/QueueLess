"""Administrative commands.

Usage (from the backend folder, with the virtualenv active):
    python -m app.cli create-superadmin --email admin@example.com --name "Platform Admin"
"""

import argparse
import getpass
import sys

from pydantic import ValidationError

from app.core.security import hash_password
from app.database import SessionLocal, init_db
from app.models import User, UserRole
from app.schemas.auth import RegisterRequest
from app.services.auth_service import get_user_by_email


def create_superadmin(email: str, full_name: str) -> int:
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match.", file=sys.stderr)
        return 1
    try:
        data = RegisterRequest(email=email, password=password, full_name=full_name)
    except ValidationError as exc:
        print(exc, file=sys.stderr)
        return 1

    init_db()
    with SessionLocal() as db:
        if get_user_by_email(db, data.email):
            print(f"A user with email {data.email} already exists.", file=sys.stderr)
            return 1
        db.add(
            User(
                email=data.email,
                full_name=data.full_name,
                hashed_password=hash_password(data.password),
                role=UserRole.SUPER_ADMIN,
            )
        )
        db.commit()
    print(f"Super admin {data.email} created.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    superadmin = commands.add_parser("create-superadmin", help="Create a SUPER_ADMIN account")
    superadmin.add_argument("--email", required=True)
    superadmin.add_argument("--name", default="Platform Admin")
    args = parser.parse_args()

    if args.command == "create-superadmin":
        return create_superadmin(args.email, args.name)
    return 1


if __name__ == "__main__":
    sys.exit(main())
