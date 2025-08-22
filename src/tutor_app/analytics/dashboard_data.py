# src/tutor_app/analytics/dashboard_data.py
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from src.tutor_app.db.models import PracticeLog, Question, KnowledgeSource
import pandas as pd
from typing import List, Optional
import datetime

def get_practice_summary(db: Session, source_ids: Optional[List[int]] = None, start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None):
    query = db.query(PracticeLog)
    if source_ids:
        query = query.join(Question, PracticeLog.question_id == Question.id).filter(Question.source_id.in_(source_ids))
    if start_date:
        query = query.filter(PracticeLog.timestamp >= start_date)
    if end_date:
        # 增加一天以包含结束日期当天
        query = query.filter(PracticeLog.timestamp < end_date + datetime.timedelta(days=1))
    
    total_practices = query.count()
    correct_practices = query.filter(PracticeLog.is_correct == True).count()
    accuracy = (correct_practices / total_practices * 100) if total_practices > 0 else 0
    return {
        "total": total_practices,
        "correct": correct_practices,
        "accuracy": round(accuracy, 2)
    }

def get_performance_by_source(db: Session, source_ids: Optional[List[int]] = None, start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None):
    query = db.query(
        KnowledgeSource.filename,
        func.count(PracticeLog.id).label('total'),
        func.sum(func.cast(PracticeLog.is_correct, Integer)).label('correct')
    ).join(Question, Question.source_id == KnowledgeSource.id)\
     .join(PracticeLog, PracticeLog.question_id == Question.id)

    if source_ids:
        query = query.filter(KnowledgeSource.id.in_(source_ids))
    if start_date:
        query = query.filter(PracticeLog.timestamp >= start_date)
    if end_date:
        query = query.filter(PracticeLog.timestamp < end_date + datetime.timedelta(days=1))

    results = query.group_by(KnowledgeSource.filename).all()
    
    if not results: return pd.DataFrame()
    df = pd.DataFrame(results, columns=['知识源', '练习次数', '正确次数'])
    df['正确率'] = (df['正确次数'] / df['练习次数'] * 100).round(2)
    return df

def get_mistake_notebook(db: Session, source_ids: Optional[List[int]] = None, start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None):
    query = db.query(Question, PracticeLog)\
                .join(PracticeLog, Question.id == PracticeLog.question_id)\
                .filter(PracticeLog.is_correct == False)

    if source_ids:
        query = query.filter(Question.source_id.in_(source_ids))
    if start_date:
        query = query.filter(PracticeLog.timestamp >= start_date)
    if end_date:
        query = query.filter(PracticeLog.timestamp < end_date + datetime.timedelta(days=1))

    mistakes = query.order_by(PracticeLog.timestamp.desc()).all()
    
    grouped_mistakes = {}
    source_cache = {} # 缓存文件名查询结果
    for question, log in mistakes:
        source_id = question.source_id
        if source_id not in grouped_mistakes:
            if source_id not in source_cache:
                source = db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
                source_cache[source_id] = source.filename if source else "未知来源"
            grouped_mistakes[source_id] = {'name': source_cache[source_id], 'mistakes': []}
        grouped_mistakes[source_id]['mistakes'].append((question, log))
        
    return grouped_mistakes