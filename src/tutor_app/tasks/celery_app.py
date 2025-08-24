# src/tutor_app/tasks/celery_app.py
from celery import Celery
from src.tutor_app.core.config import settings
from src.tutor_app.core.logging import setup_logging # <<< 导入

setup_logging() # <<< 在Celery应用创建前调用
# 使用Redis作为Broker
celery_app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    # 在列表中加入新的任务文件
    include=["src.tutor_app.tasks.processing", "src.tutor_app.tasks.generation","src.tutor_app.tasks.grading"]
)

celery_app.conf.update(
    task_track_started=True,
)