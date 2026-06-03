from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── OpenAI  ──────────────────
    openai_api_key: str = ""

    # ── Free LLM providers ───────────────────────────────────────────────
    groq_api_key: str = ""          
    gemini_api_key: str = ""        
    huggingface_api_key: str = ""   

    # ── Vector DB ────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"

    # ── LLM model names  ────────────────────
    groq_model: str = "llama-3.1-8b-instant"
    gemini_model: str = "gemini-1.5-flash"
    huggingface_model: str = "HuggingFaceH4/zephyr-7b-beta"

    # ── Embedding — local HuggingFace  ────────────────
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── App ───────────────────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()