from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lygre API"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    # Default to a local sqlite DB for developer runs (overridden in production via env)
    database_url: str = "sqlite:////workspaces/lygre/backend/dev.db"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 30
    refresh_token_expires_days: int = 14
    seed_admin_email: str = "admin@lygre.local"
    seed_admin_name: str = "Default Admin"
    seed_admin_password: str = "Admin123!"
    # ensure default uploads dir is writable in local dev container
    uploads_dir: str = "/workspaces/lygre/backend/uploads"
    uploads_dir_host: str = "/workspaces/lygre/backend/uploads"
    # By default allow local frontend origins for developer runs; production should override via env
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    # toggle production-level fail-fast checks (set LYGRE_PRODUCTION=1 in env)
    is_production: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


settings = Settings()
