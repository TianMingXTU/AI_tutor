# src/tutor_app/llms/llm_factory.py

from langchain_community.embeddings import OllamaEmbeddings
from langchain_ollama import ChatOllama
from src.tutor_app.core.config import settings

def get_chat_model():
    """
    返回一个连接到本地Ollama的聊天模型实例。
    """
    print(f"Initializing Ollama Chat Model: {settings.OLLAMA_CHAT_MODEL}")
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_CHAT_MODEL,
        temperature=0.7,
    )

def get_embedding_model():
    """
    【优化版】返回一个使用 .env 中详细配置的嵌入模型实例。
    """
    print(f"Initializing Ollama Embedding Model: {settings.EMBEDDING_MODEL_NAME}")
    return OllamaEmbeddings(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.EMBEDDING_MODEL_NAME,
    )