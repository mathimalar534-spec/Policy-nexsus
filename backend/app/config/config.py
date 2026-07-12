import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    # App General Settings
    APP_NAME: str = "Policy Conflict & Staleness Detector"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # Security & Auth
    SECRET_KEY: str = "supersecretkey_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/policy_detector"
    # Fallback to sqlite locally if needed
    TEST_DATABASE_URL: str = "sqlite:///./test.db"

    # Celery & Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Uploads
    UPLOAD_DIR: str = "C:/Users/ASUS/.gemini/antigravity/scratch/policy_detector/uploads"
    SAMPLE_DATA_DIR: str = "C:/Users/ASUS/.gemini/antigravity/scratch/sample_data"

    # Stale Detector Rules
    STALE_POLICY_THRESHOLD_DAYS: int = 365  # 1 year
    DEPRECATED_TECHNOLOGIES: List[str] = [
        "SHA1", "SHA-1", "DES", "3DES", "RC4", "MD5", "WEP", "WPA1",
        "SSL", "SSLv2", "SSLv3", "TLS1.0", "TLS 1.0", "TLS1.1", "TLS 1.1",
        "FTP", "Telnet", "Windows Server 2008", "Windows Server 2012", 
        "Windows XP", "Windows 7"
    ]

    # Embeddings & Vector Store
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    FAISS_INDEX_PATH: str = "C:/Users/ASUS/.gemini/antigravity/scratch/policy_detector/faiss_index"

    # LLM Settings (Ollama or OpenAI Compatible)
    LLM_API_TYPE: str = "openai"  # "openai" or "ollama" or "mock"
    LLM_API_KEY: str = "mock-key"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    
    # Ollama settings fallback
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Initialize settings
settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.FAISS_INDEX_PATH, exist_ok=True)
