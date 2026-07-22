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
    llm_enabled: bool = False
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(env_file=".env", env_prefix="BIA_", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_available(self) -> bool:
        return self.llm_enabled and bool(self.llm_api_key and self.llm_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
