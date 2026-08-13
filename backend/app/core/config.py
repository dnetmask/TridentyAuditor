from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TRIDENTY_")

    environment: str = "local"

    database_url: str = (
        "postgresql+psycopg2://tridenty:tridenty@localhost:5432/tridentyauditor"
    )

    # Placeholder JWT verification until Keycloak/OIDC federation lands (Fase 2,
    # sección 05 del documento de arquitectura). Tokens are expected to carry
    # `tenant_id`, `sub` and `role` claims.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"

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

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
