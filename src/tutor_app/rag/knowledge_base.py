# src/tutor_app/rag/knowledge_base.py
import os
import tiktoken
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from src.tutor_app.llms.llm_factory import get_embedding_model
from src.tutor_app.core.config import settings # <<< 导入settings

CHROMA_PERSIST_DIRECTORY = "data/chroma_db"

def process_and_vectorize_file(filepath: str, source_id: int):
    """
    【最终优化版】加载PDF文件，使用 .env 中配置的参数进行动态切分。
    """
    print(f"Processing file: {filepath} for source_id: {source_id}")
    
    # 1. 加载文档
    loader = PyPDFLoader(filepath)
    documents = loader.load()

    # 2. 【核心优化】使用 .env 中的配置来创建文本分割器
    print(f"Using chunk settings: size={settings.EMBEDDING_CHUNK_SIZE}, overlap={settings.EMBEDDING_CHUNK_OVERLAP}")
    
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoding = tiktoken.get_encoding("gpt2")

    def tiktoken_len(text):
        return len(encoding.encode(text))

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.EMBEDDING_CHUNK_SIZE,
        chunk_overlap=settings.EMBEDDING_CHUNK_OVERLAP,
        length_function=tiktoken_len,
    )
    splits = text_splitter.split_documents(documents)
    print(f"文件被切分为 {len(splits)} 个文本块。")

    # 3. 更新每个文档块的元数据
    for split in splits:
        if split.metadata is None:
            split.metadata = {}
        split.metadata['source_id'] = str(source_id)

    # 4. 创建嵌入并存入ChromaDB
    embedding_model = get_embedding_model()
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embedding_model,
        persist_directory=CHROMA_PERSIST_DIRECTORY
    )
    
    print(f"Successfully processed and vectorized file for source_id: {source_id}")
    return True