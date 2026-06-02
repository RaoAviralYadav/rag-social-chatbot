from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # API Keys
    openai_api_key: str = ""

    # Vector DB
    chroma_persist_dir: str = "./chroma_db"

    # LLM / Embeddings
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # App
    cors_origins: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()