from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "support_knowledge"
    database_path: str = "support.db"
    starter_knowledge_path: str = "../knowledge-base/starter-faq.md"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_provider: str = "extractive"
    groq_api_key: str = ""
    google_api_key: str = ""
    mistral_api_key: str = ""
    escalation_threshold: float = 0.35
    cors_origins: str = "http://localhost:3000"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
