# src/tutor_app/crud/crud_question.py
from sqlalchemy.orm import Session
from sqlalchemy import func, not_
from src.tutor_app.db.models import Question, PracticeLog, KnowledgeSource # 引入PracticeLog和KnowledgeSource
import json
import random


def create_question(db: Session, source_id: int, question_data: dict):
    """
    将一道生成好的题目存入数据库
    """
    question = Question(
        source_id=source_id,
        question_type=question_data.get("question_type"),
        content=json.dumps(question_data.get("content")), # 将字典转为JSON字符串
        answer=json.dumps(question_data.get("answer")),
        analysis=question_data.get("analysis"),
        knowledge_tag=question_data.get("knowledge_tag")
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def get_random_question_by_mode(db: Session, mode: str):
    """
    根据不同模式获取一道随机题目。
    """
    query = None
    if mode == "只刷新题":
        # 找到所有在 PracticeLog 中没有记录的题目ID
        answered_question_ids = db.query(PracticeLog.question_id).distinct()
        query = db.query(Question).filter(not_(Question.id.in_(answered_question_ids)))

    elif mode == "只刷错题":
        # 找到所有被答错的题目ID
        incorrect_question_ids = db.query(PracticeLog.question_id).filter(PracticeLog.is_correct == False).distinct()
        if not incorrect_question_ids.all():
            return None # 如果没有错题，返回None
        query = db.query(Question).filter(Question.id.in_(incorrect_question_ids))

    elif mode == "混合模式":
        # 简单实现：随机从所有题目中抽取
        query = db.query(Question)

    if query:
        # 从查询结果中随机选择一个
        count = query.count()
        if count > 0:
            random_offset = random.randint(0, count - 1)
            return query.offset(random_offset).first()

    return None

def create_practice_log(db: Session, question_id: int, user_answer: str, is_correct: bool):
    """
    记录一次刷题尝试。
    """
    log_entry = PracticeLog(
        question_id=question_id,
        user_answer=user_answer,
        is_correct=is_correct
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

# src/tutor_app/crud/crud_question.py
# ... (保留已有函数)
from src.tutor_app.db.models import Exam, ExamResult

def get_questions_for_exam(db: Session, source_id: int, num_questions: int):
    """为一场考试从指定知识源随机抽取题目"""
    query = db.query(Question).filter(Question.source_id == source_id)
    count = query.count()

    # 如果题库数量不足，则取所有题目
    num_to_fetch = min(count, num_questions)
    if num_to_fetch == 0:
        return []

    return query.order_by(func.random()).limit(num_to_fetch).all()

def save_exam_and_get_id(db: Session, source_id: int, title: str, question_ids: list):
    """保存一场考试的定义并返回其ID"""
    exam = Exam(source_id=source_id, title=title, question_ids=question_ids)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam.id

def save_exam_result(db: Session, exam_id: int, score: int, total: int, user_answers: dict):
    """保存一次考试的结果"""
    result = ExamResult(exam_id=exam_id, score=score, total=total, user_answers=user_answers)
    db.add(result)
    db.commit()
    db.refresh(result)
    return result

# src/tutor_app/crud/crud_question.py

# ... (保留所有已有函数)

def get_question_batch_by_mode(db: Session, mode: str, count: int = 20):
    """
    根据模式批量获取一批题目用于练习或考试。
    """
    query = None
    if mode == "只刷新题":
        answered_question_ids = db.query(PracticeLog.question_id).distinct()
        query = db.query(Question).filter(not_(Question.id.in_(answered_question_ids)))

    elif mode == "只刷错题":
        incorrect_question_ids = db.query(PracticeLog.question_id).filter(PracticeLog.is_correct == False).distinct()
        if not incorrect_question_ids.all():
            return [] # 如果没有错题，返回空列表
        query = db.query(Question).filter(Question.id.in_(incorrect_question_ids))

    elif mode == "混合模式":
        query = db.query(Question)

    if query:
        # 从查询结果中随机选择指定数量的题目
        total_count = query.count()
        num_to_fetch = min(total_count, count)
        if num_to_fetch > 0:
            return query.order_by(func.random()).limit(num_to_fetch).all()

    return []

# src/tutor_app/crud/crud_question.py
# ... (保留已有函数)
import datetime
from src.tutor_app.db.models import UserQuestionStats
from src.tutor_app.core.srs_logic import update_srs_stats

def get_review_questions(db: Session, user_id: int = 1, count: int = 20):
    """获取今天需要复习的题目"""
    today = datetime.date.today()

    # 查找所有记忆档案中今天或之前应该复习的题目ID
    review_q_ids_query = db.query(UserQuestionStats.question_id)\
                           .filter(UserQuestionStats.user_id == user_id, 
                                   UserQuestionStats.next_review_date <= today)

    # 从Question表中获取这些题目
    query = db.query(Question).filter(Question.id.in_(review_q_ids_query))

    total_count = query.count()
    num_to_fetch = min(total_count, count)
    if num_to_fetch > 0:
        return query.order_by(func.random()).limit(num_to_fetch).all()
    return []

def update_question_stats(db: Session, question_id: int, quality: int, user_id: int = 1):
    """更新一道题的记忆状态"""
    # 查找该题是否已有记忆档案，没有则创建
    stats = db.query(UserQuestionStats).filter_by(user_id=user_id, question_id=question_id).first()
    if not stats:
        stats = UserQuestionStats(user_id=user_id, question_id=question_id)
        db.add(stats)

    # 使用SRS算法更新状态
    updated_stats = update_srs_stats(stats, quality)

    db.commit()
    return updated_stats

# src/tutor_app/crud/crud_question.py

# ... (保留所有已有函数)
from typing import Dict, Optional, List

def get_question_batch_with_type_selection(
    db: Session, 
    mode: str, 
    type_counts: Dict[str, int], 
    source_ids: Optional[List[int]] = None
):
    """
    【全新】根据用户选择的题型和数量，批量获取题目。
    type_counts: 一个字典，例如 {'单项选择题': 10, '判断题': 5}
    """
    all_questions = []
    
    # 定义题目的展示顺序
    type_order = ["单项选择题", "判断题", "填空题", "简答题"]

    # 为了保证最终输出的顺序，我们按预设的顺序来查询
    for question_type in type_order:
        if question_type in type_counts and type_counts[question_type] > 0:
            count = type_counts[question_type]
            
            # 复用之前的查询逻辑来构建基础查询
            query = None
            if mode == "只刷新题":
                answered_question_ids = db.query(PracticeLog.question_id).distinct()
                query = db.query(Question).filter(not_(Question.id.in_(answered_question_ids)))
            elif mode == "只刷错题":
                incorrect_question_ids = db.query(PracticeLog.question_id).filter(PracticeLog.is_correct == False).distinct()
                if not incorrect_question_ids.all(): continue
                query = db.query(Question).filter(Question.id.in_(incorrect_question_ids))
            else: # 混合模式或智能复习
                query = db.query(Question)
            
            # 在基础查询上增加题型和知识源筛选
            query = query.filter(Question.question_type == question_type)
            if source_ids:
                query = query.filter(Question.source_id.in_(source_ids))

            # 获取指定数量的题目
            total_count = query.count()
            num_to_fetch = min(total_count, count)
            if num_to_fetch > 0:
                fetched_questions = query.order_by(func.random()).limit(num_to_fetch).all()
                all_questions.extend(fetched_questions)

    return all_questions

# src/tutor_app/crud/crud_question.py

# ... (保留所有已有函数)

def count_questions_by_source(db: Session, source_id: int) -> int:
    """计算一个特定知识源下有多少道题目"""
    return db.query(Question).filter(Question.source_id == source_id).count()

def delete_source_and_related_data(db: Session, source_id: int):
    """删除一个知识源及其所有关联的题目和练习记录"""
    # 警告：这是一个危险操作，会级联删除
    
    # 1. 找到所有关联的题目ID
    question_ids_to_delete = db.query(Question.id).filter(Question.source_id == source_id).all()
    if question_ids_to_delete:
        # 将元组列表转换为ID列表
        q_ids = [q_id[0] for q_id in question_ids_to_delete]
        
        # 2. 删除与这些题目相关的所有练习记录和考试结果
        # (为简化，此处只删除练习记录，您可以按需扩展)
        db.query(PracticeLog).filter(PracticeLog.question_id.in_(q_ids)).delete(synchronize_session=False)

        # 3. 删除所有关联的题目
        db.query(Question).filter(Question.id.in_(q_ids)).delete(synchronize_session=False)

    # 4. 删除知识源本身
    db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).delete(synchronize_session=False)
    
    db.commit()

def get_recent_sources(db: Session, limit: int = 5):
    """获取最近上传的几个知识源"""
    return db.query(KnowledgeSource).order_by(KnowledgeSource.created_at.desc()).limit(limit).all()

# src/tutor_app/crud/crud_question.py
# ... (保留所有已有函数)
def get_questions_by_ids(db: Session, question_ids: List[int]):
    """根据一个ID列表，获取所有对应的Question对象"""
    if not question_ids:
        return []
    return db.query(Question).filter(Question.id.in_(question_ids)).all()