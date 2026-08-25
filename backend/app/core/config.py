from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "dev-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TRIDENTY_")

    environment: str = "local"

    database_url: str = (
        "postgresql+psycopg2://tridenty:tridenty@localhost:5432/tridentyauditor"
    )
    # URL con el rol DUEÑO de las tablas, solo para correr migraciones. La app
    # debe conectarse con un rol sin SUPERUSER ni ownership (los superusuarios
    # y los dueños con FORCE RLS a medias anulan el aislamiento por RLS — ver
    # deploy/db-init/). Si no se define, alembic cae a database_url (útil en
    # desarrollo local, donde un solo rol no-superusuario hace ambos papeles).
    migrations_database_url: str | None = None

    # Placeholder JWT verification until Keycloak/OIDC federation lands (Fase 2,
    # sección 05 del documento de arquitectura).
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    # Vida del access token. Corto a propósito: la sesión larga vive en el
    # refresh token (revocable en BD), no en el JWT.
    access_token_minutes: int = 60
    refresh_token_days: int = 14

    # Candado anti fuerza bruta del login. El lockout por cuenta persiste en
    # BD (users.locked_until); este límite por IP es una primera barrera en
    # memoria, por réplica. 0 = deshabilitado (solo para suites de prueba).
    login_rate_limit_per_minute: int = 30
    login_lockout_attempts: int = 5
    login_lockout_minutes: int = 15

    # Origins allowed to call the API from a browser (the Vite dev server by
    # default). Comma-separated.
    cors_origins: str = "http://localhost:5173"

    # Bootstrap opcional de la primera cuenta Super Admin al arrancar (útil en
    # despliegues de contenedor donde no hay una terminal a mano para correr
    # scripts/create_super_admin.py — ver TridentyOT como referencia de este
    # patrón). Sin estas dos variables no pasa nada; con solo una definida, el
    # arranque falla con un error claro en vez de crear una cuenta a medias.
    super_admin_email: str | None = None
    super_admin_password: str | None = None
    super_admin_name: str = "Super Admin"

    # Almacenamiento de los binarios de MOD·DOC — disco local bajo un volumen
    # (coherente con el tier on-prem/air-gapped de la sección 04: funciona sin
    # ningún servicio externo). Migrar a Object Storage S3-compatible con
    # política WORM es trabajo pendiente de hardening para producción, no de
    # esta fase (ver docs/modules/mod-doc.md).
    documents_storage_dir: str = "./data/documents"
    documents_max_file_size_mb: int = 25
    # Tope duro para cualquier request con Content-Length declarado — un poco
    # por encima del máximo de archivo para dejar espacio al overhead multipart.
    max_request_body_mb: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_local(self) -> bool:
        return self.environment.lower() in ("local", "dev", "development", "test")

    def assert_production_ready(self) -> None:
        """Aborta el arranque si la configuración es insegura fuera de local.

        La alternativa — arrancar igual y confiar en que alguien lea un
        warning — es exactamente como el secreto default termina firmando
        tokens en producción.
        """
        if self.is_local:
            return
        problems: list[str] = []
        if self.jwt_secret == _DEFAULT_JWT_SECRET:
            problems.append(
                "TRIDENTY_JWT_SECRET sigue siendo el default del repositorio; "
                "cualquiera puede forjar tokens con él"
            )
        elif len(self.jwt_secret) < 32:
            problems.append("TRIDENTY_JWT_SECRET debe tener al menos 32 caracteres")
        insecure_origins = [
            origin for origin in self.cors_origin_list
            if origin == "*" or not origin.startswith("https://")
        ]
        if insecure_origins:
            problems.append(
                "TRIDENTY_CORS_ORIGINS debe listar solo orígenes https:// explícitos "
                f"fuera de local (inválidos: {', '.join(insecure_origins)})"
            )
        if problems:
            raise RuntimeError(
                f"Configuración insegura para environment='{self.environment}': "
                + " · ".join(problems)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
