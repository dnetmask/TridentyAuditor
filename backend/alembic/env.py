from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import models so they register on Base.metadata before autogenerate/create.
from app.activity import models as activity_models  # noqa: F401
from app.audit import models as audit_models  # noqa: F401
from app.auth import models as auth_models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base
from app.documents import models as documents_models  # noqa: F401
from app.frameworks import models as frameworks_models  # noqa: F401
from app.risk import models as risk_models  # noqa: F401
from app.soa import models as soa_models  # noqa: F401
from app.tenants import models as tenants_models  # noqa: F401
from app.wizard import models as wizard_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Las migraciones corren con el rol DUEÑO de las tablas; la app con un rol
# sin ownership ni SUPERUSER (RLS real). Si no hay URL de migraciones
# separada (desarrollo local), se usa la misma de la app.
_settings = get_settings()
config.set_main_option(
    "sqlalchemy.url", _settings.migrations_database_url or _settings.database_url
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
