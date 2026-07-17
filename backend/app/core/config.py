from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BOM Impact Analyzer"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/bom.db"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    upload_max_mb: int = 20
    upload_dir: str = "./data/uploads"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="BIA_", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

