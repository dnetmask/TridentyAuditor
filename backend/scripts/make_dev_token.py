#!/usr/bin/env python3
"""Mints a JWT for local development, stand-in for Keycloak/OIDC (Fase 2).

Usage:
    python scripts/make_dev_token.py <tenant_id> [--sub user@example.com] [--role admin]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import jwt

from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tenant_id", help="UUID of the tenant to embed in the token")
    parser.add_argument("--sub", default="dev-user", help="Subject / user id")
    parser.add_argument("--role", default="tenant_admin", help="Role claim")
    args = parser.parse_args()

    settings = get_settings()
    token = jwt.encode(
        {"tenant_id": args.tenant_id, "sub": args.sub, "role": args.role},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    print(token)


if __name__ == "__main__":
    main()
