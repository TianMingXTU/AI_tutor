# src/tutor_app/rag/knowledge_base.py
import os
import tiktoken
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredMarkdownLoader # 【优化1】导入新的Loader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from src.tutor_app.llms.llm_factory import get_embedding_model
from src.tutor_app.core.config import settings

CHROMA_PERSIST_DIRECTORY = "data/chroma_db"

def process_and_vectorize_file(filepath: str, source_id: int):
    """
    【V3 优化版】根据文件类型动态选择加载器，支持 PDF, DOCX, MD。
    """
    print(f"Processing file: {filepath} for source_id: {source_id}")
    
    # --- 【优化2】动态加载器选择逻辑 ---
    _, file_extension = os.path.splitext(filepath)
    file_extension = file_extension.lower()

    if file_extension == ".pdf":
        loader = PyPDFLoader(filepath)
    elif file_extension == ".docx":
        loader = Docx2txtLoader(filepath)
    elif file_extension == ".md":
        loader = UnstructuredMarkdownLoader(filepath)
    else:
        raise ValueError(f"不支持的文件类型: {file_extension}")

    print(f"检测到文件类型: '{file_extension}', 使用 {loader.__class__.__name__} 加载器。")
    documents = loader.load()
    # --- 逻辑结束 ---

    # 2. 【核心优化】使用 .env 中的配置来创建文本分割器 (此部分逻辑不变)
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

    # 3. 更新每个文档块的元数据 (此部分逻辑不变)
    for split in splits:
        if split.metadata is None:
            split.metadata = {}
        split.metadata['source_id'] = str(source_id)

    # 4. 创建嵌入并存入ChromaDB (此部分逻辑不变)
    embedding_model = get_embedding_model()
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embedding_model,
        persist_directory=CHROMA_PERSIST_DIRECTORY
    )
    
    print(f"Successfully processed and vectorized file for source_id: {source_id}")
    return True