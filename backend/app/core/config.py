from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lygre API"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/lygre"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 30
    refresh_token_expires_days: int = 14
    seed_admin_email: str = "admin@lygre.local"
    seed_admin_name: str = "Default Admin"
    seed_admin_password: str = "Admin123!"
    uploads_dir: str = "/app/uploads"
    uploads_dir_host: str = "/workspaces/lygre/backend/uploads"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


settings = Settings()
