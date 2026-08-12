#!/usr/bin/env python3
"""Crea la primera cuenta Super Admin directamente en la base de datos.

No hay huevo-o-gallina: sin esto, nadie podría llamar a POST /api/v1/auth/users
para crear la primera cuenta, porque ese endpoint ya exige estar autenticado
como Super Admin o Admin del tenant.

Usage:
    python scripts/create_super_admin.py admin@netmask.co --name "Nombre Apellido"
"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.models import User, UserRole  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.tenants import models as _tenants_models  # noqa: E402,F401 — registra la tabla tenants para el FK


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email")
    parser.add_argument("--name", required=True, help="Nombre completo")
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirmar password: ")
    if password != confirm:
        print("Las contraseñas no coinciden", file=sys.stderr)
        sys.exit(1)
    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        email = args.email.lower()
        if db.query(User).filter_by(email=email).one_or_none() is not None:
            print(f"Ya existe un usuario con el email {email}", file=sys.stderr)
            sys.exit(1)

        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=args.name,
            role=UserRole.SUPER_ADMIN,
            tenant_id=None,
        )
        db.add(user)
        db.commit()
        print(f"Super Admin creado: {user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
