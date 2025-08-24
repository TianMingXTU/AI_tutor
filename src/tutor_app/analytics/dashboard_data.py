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

# src/tutor_app/analytics/dashboard_data.py
# ... (保留所有已有的 import 和函数)

def get_performance_by_tag(db: Session, source_ids: Optional[List[int]] = None, start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None):
    """
    【全新】按知识点标签聚合分析练习表现。
    """
    # 基础查询，连接 PracticeLog 和 Question 表
    query = db.query(
        Question.knowledge_tag,
        func.count(PracticeLog.id).label('total'),
        func.sum(func.cast(PracticeLog.is_correct, Integer)).label('correct')
    ).join(PracticeLog, PracticeLog.question_id == Question.id)

    # 应用筛选条件
    if source_ids:
        # 知识源筛选需要再次 join KnowledgeSource 表
        query = query.filter(Question.source_id.in_(source_ids))
    if start_date:
        query = query.filter(PracticeLog.timestamp >= start_date)
    if end_date:
        query = query.filter(PracticeLog.timestamp < end_date + datetime.timedelta(days=1))

    # 过滤掉没有知识点标签的题目
    query = query.filter(Question.knowledge_tag.isnot(None)).filter(Question.knowledge_tag != '')
    
    # 按知识点标签分组
    results = query.group_by(Question.knowledge_tag).all()
    
    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results, columns=['知识点', '练习次数', '正确次数'])
    df['正确率'] = (df['正确次数'] / df['练习次数'] * 100).round(2)
    return df

# src/tutor_app/analytics/dashboard_data.py
# ... (保留所有已有的 import 和函数)
from sqlalchemy import select

def get_knowledge_network_data(db: Session):
    """
    【全新】查询数据库，为知识网络图提供节点和边的数据。
    """
    # 1. 查询所有知识源作为一级节点
    sources = db.query(KnowledgeSource).all()
    
    # 2. 查询所有独特的知识点标签及其来源ID
    #    这会得到一个 (knowledge_tag, source_id) 的元组列表
    query = select(Question.knowledge_tag, Question.source_id)\
            .where(Question.knowledge_tag.isnot(None) & (Question.knowledge_tag != ''))\
            .distinct()
    tag_source_pairs = db.execute(query).all()

    nodes = []
    edges = []
    
    # 创建知识源节点
    for source in sources:
        nodes.append({
            "id": f"source_{source.id}", 
            "label": source.filename, 
            "type": "source"
        })

    # 创建知识点节点和边
    existing_tags = set()
    for tag, source_id in tag_source_pairs:
        # 添加知识点节点（如果尚未添加）
        if tag not in existing_tags:
            nodes.append({
                "id": tag,
                "label": tag,
                "type": "tag"
            })
            existing_tags.add(tag)
        
        # 添加从知识源指向知识点的边
        edges.append({
            "from": f"source_{source_id}",
            "to": tag
        })
        
    return nodes, edges

# src/tutor_app/analytics/dashboard_data.py
# ... (保留所有已有 import 和函数)
from src.tutor_app.db.models import UserQuestionStats
from sqlalchemy import select

def get_srs_review_forecast(db: Session, days: int = 30, user_id: int = 1):
    """
    【新增】获取未来一段时间内，每天需要复习的题目数量。
    """
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=days)
    
    # 查询 UserQuestionStats 表中未来 'days' 天内需要复习的记录
    query = select(UserQuestionStats.next_review_date, func.count(UserQuestionStats.id).label('count'))\
            .where(UserQuestionStats.user_id == user_id)\
            .where(UserQuestionStats.next_review_date.between(today, end_date))\
            .group_by(UserQuestionStats.next_review_date)\
            .order_by(UserQuestionStats.next_review_date)
            
    results = db.execute(query).all()

    if not results:
        return pd.DataFrame({'日期': pd.to_datetime([]), '待复习数': []}).set_index('日期')

    # 将结果转换为pandas DataFrame，方便绘图
    df = pd.DataFrame(results, columns=['日期', '待复习数'])
    df['日期'] = pd.to_datetime(df['日期'])
    
    # 创建一个完整日期范围的索引，填充缺失的日期
    full_date_range = pd.date_range(start=today, end=end_date, freq='D')
    df = df.set_index('日期').reindex(full_date_range, fill_value=0)
    
    return df

def get_hardest_questions(db: Session, limit: int = 10, user_id: int = 1):
    """
    【新增】获取简易度因子(ease_factor)最低的N个题目，即最难的题目。
    """
    query = db.query(Question, UserQuestionStats)\
              .join(UserQuestionStats, Question.id == UserQuestionStats.question_id)\
              .filter(UserQuestionStats.user_id == user_id)\
              .order_by(UserQuestionStats.ease_factor.asc())\
              .limit(limit)
              
    return query.all()

# src/tutor_app/analytics/dashboard_data.py
# ... (保留所有已有函数)

def get_current_user_stats(db: Session):
    """
    【新增】获取当前用户（单用户模式）的学习总览数据。
    """
    total_practices = db.query(PracticeLog).count()
    total_correct = db.query(PracticeLog).filter(PracticeLog.is_correct == True).count()
    
    return {
        "username": "我 (You)",
        "total_practices": total_practices,
        "total_correct": total_correct
    }