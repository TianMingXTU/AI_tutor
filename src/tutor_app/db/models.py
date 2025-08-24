# src/tutor_app/db/models.py
import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    Text,
)
from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    status = Column(String, default="pending")  # e.g., pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, nullable=False) # Foreign key to KnowledgeSource in the future
    question_type = Column(String, nullable=False) # 'multiple_choice', 'short_answer', etc.
    content = Column(JSON, nullable=False) # For MCQs: {'question': '..', 'options': ['A', 'B', 'C', 'D']}
    answer = Column(JSON, nullable=False) # For MCQs: {'correct_option': 'A'}
    analysis = Column(Text, nullable=True) # Detailed explanation
    knowledge_tag = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PracticeLog(Base):
    __tablename__ = "practice_logs"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

     # 【新增字段】
    ai_score = Column(String, nullable=True)     # e.g., "正确", "部分正确", "错误"
    ai_feedback = Column(Text, nullable=True)    # 存储AI给出的详细评语

# src/tutor_app/db/models.py
# ... (保留所有已有的模型)

class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("knowledge_sources.id"), nullable=False)
    title = Column(String)
    question_ids = Column(JSON, nullable=False) # 存储本次考试包含的所有问题ID
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# src/tutor_app/db/models.py
# ... (保留所有已有的模型)

class ExamResult(Base):
    __tablename__ = "exam_results"
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    score = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    user_answers = Column(JSON, nullable=False)
    # 【新增字段】用于存储 {question_id: log_id} 的映射
    grading_log_ids = Column(JSON, nullable=True) 
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)
# src/tutor_app/db/models.py
# ... (保留所有已有的 imports 和模型)
from sqlalchemy import Float, Date

class UserQuestionStats(Base):
    """
    用于追踪用户对每个题目的掌握情况，实现SRS。
    """
    __tablename__ = "user_question_stats"

    id = Column(Integer, primary_key=True, index=True)
    # 假设我们只有一个用户，user_id可以默认为1
    user_id = Column(Integer, default=1, nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)

    # SM-2算法的核心参数
    repetitions = Column(Integer, default=0) # 正确复习次数
    ease_factor = Column(Float, default=2.5) # 简易度因子
    interval = Column(Integer, default=0) # 下次复习的间隔天数

    next_review_date = Column(Date, default=datetime.date.today, index=True) # 下次应复习的日期