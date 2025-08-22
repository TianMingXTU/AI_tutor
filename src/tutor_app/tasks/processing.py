# src/tutor_app/tasks/processing.py
from .celery_app import celery_app
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.db.models import KnowledgeSource
from src.tutor_app.rag.knowledge_base import process_and_vectorize_file
import os

UPLOAD_DIRECTORY = "data/uploaded_files"

@celery_app.task(bind=True)
def process_file_task(self, source_id: int):
    """
    一个Celery任务，用于在后台处理上传的文件。
    """
    db = SessionLocal()
    source = db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()

    if not source:
        print(f"Error: Could not find KnowledgeSource with id {source_id}")
        return "Failed: Source not found"

    filepath = os.path.join(UPLOAD_DIRECTORY, source.filename)

    try:
        print(f"Celery task started for source_id: {source_id}")
        # 更新状态为处理中
        source.status = "processing"
        db.commit()

        # 执行核心的RAG处理
        process_and_vectorize_file(filepath, source_id)

        # 更新状态为完成
        source.status = "completed"
        db.commit()
        print(f"Celery task completed for source_id: {source_id}")
        return "Success"

    except Exception as e:
        source.status = "failed"
        db.commit()
        print(f"Celery task failed for source_id: {source_id}. Error: {e}")
        return f"Failed: {e}"
    finally:
        db.close()