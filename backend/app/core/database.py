from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata_naming_convention = NAMING_CONVENTION


Base.metadata.naming_convention = NAMING_CONVENTION


def get_db() -> Generator[Session, None, None]:
    """Session for framework-agnostic reference data that isn't tenant-scoped."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_tenant_db_session(tenant_id: str) -> Generator[Session, None, None]:
    """Session scoped to a tenant via Postgres RLS.

    Runs ``SET LOCAL app.tenant_id`` inside the same transaction used to serve
    the request, so every query against a tenant-scoped table (RLS policy
    ``USING (tenant_id = current_setting('app.tenant_id')::uuid)``) is
    automatically filtered — the application code never adds a manual
    ``WHERE tenant_id = ...`` clause. See docs/architecture, sección 04.
    """
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
