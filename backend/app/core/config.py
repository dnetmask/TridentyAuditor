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

    # Guards the tenant-provisioning endpoint until Super Admin auth via
    # Keycloak is wired up. Temporary — see docs/modules/README.md.
    admin_bootstrap_token: str = "dev-admin-token-change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
