# src/tutor_app/core/logging.py
import logging
import sys
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

def setup_logging():
    """配置全局日志记录器"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # 创建一个通用的格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 获取根记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 防止重复添加handler
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 1. 配置输出到文件的Handler
    # RotatingFileHandler可以在文件达到一定大小时自动创建新文件
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 2. 配置输出到控制台的Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.info("日志系统已成功初始化。")