# src/tutor_app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    
    # Ollama 聊天模型配置
    OLLAMA_BASE_URL: str
    OLLAMA_CHAT_MODEL: str
    
    # 【核心优化】Ollama 嵌入模型配置
    EMBEDDING_MODEL_NAME: str
    EMBEDDING_CHUNK_SIZE: int
    EMBEDDING_CHUNK_OVERLAP: int

    class Config:
        env_file = ".env"

settings = Settings()