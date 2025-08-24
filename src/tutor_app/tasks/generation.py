# src/tutor_app/tasks/generation.py
import gevent
from .celery_app import celery_app
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.rag.question_generator import get_questions_chain
from src.tutor_app.crud.crud_question import create_question
from src.tutor_app.rag.json_parser import parse_json_with_ai_fallback
from src.tutor_app.schemas.question import (
    MultipleChoiceQuestionSchema, TrueFalseQuestionSchema, 
    ShortAnswerQuestionSchema, FillInTheBlankQuestionSchema
)
from pydantic import ValidationError
from typing import Dict

SCHEMA_MAP = {
    "单项选择题": MultipleChoiceQuestionSchema, "判断题": TrueFalseQuestionSchema,
    "简答题": ShortAnswerQuestionSchema, "填空题": FillInTheBlankQuestionSchema
}

def _generate_and_validate_question(rag_chain, question_type, schema):
    """
    【同步辅助函数】生成、解析并校验单个问题。
    这个函数会被gevent并发执行。
    """
    try:
        llm_output_string = rag_chain.invoke(question_type)
        parsed_data = parse_json_with_ai_fallback(llm_output_string)
        if parsed_data:
            validated_data = schema(**parsed_data)
            return validated_data.dict()
    except ValidationError as e:
        print(f"Warning: Pydantic validation failed for {question_type}. Error: {e}")
    except Exception as e:
        print(f"Warning: An unexpected error occurred during single generation. Error: {e}")
    return None

# src/tutor_app/tasks/generation.py

# ... (文件顶部的 aimport 和常量保持不变)

@celery_app.task(bind=True)
def generate_questions_task(self, source_id: int, type_counts: Dict[str, int]):
    """
    【全新Gevent并行版 - V2 优化版】Celery任务，提供更精细的进度反馈。
    """
    total_requested = sum(type_counts.values())
    print(f"Starting Gevent PARALLEL generation for source_id: {source_id}, request: {type_counts}")
    self.update_state(state='PROGRESS', meta={'current': 0, 'total': total_requested, 'status': '正在初始化AI引擎...'})

    all_jobs = []
    # 1. 为每一个要生成的题目创建一个gevent“作业”（Greenlet）
    for q_type, num_questions in type_counts.items():
        if q_type not in SCHEMA_MAP: continue
        schema = SCHEMA_MAP[q_type]
        rag_chain = get_questions_chain(q_type, source_id)
        for _ in range(num_questions):
            job = gevent.spawn(_generate_and_validate_question, rag_chain, q_type, schema)
            all_jobs.append(job)

    # 【优化1】在AI生成期间更新状态
    self.update_state(state='PROGRESS', meta={'current': 0, 'total': total_requested, 'status': f'已提交 {len(all_jobs)} 个生成请求，等待AI批量处理...'})
    
    # 2. 等待所有并发的“作业”完成
    print(f"Executing {len(all_jobs)} generation jobs in parallel with gevent...")
    gevent.joinall(all_jobs)
    
    # 3. 收集结果
    valid_questions = [job.value for job in all_jobs if job.value is not None]
    generated_count = len(valid_questions)
    
    # 【优化2】在存入数据库前更新状态
    self.update_state(state='PROGRESS', meta={'current': generated_count, 'total': total_requested, 'status': f'AI处理完成，正在将 {generated_count} 道题存入数据库...'})

    # 4. 存入数据库
    db = SessionLocal()
    try:
        for question_data in valid_questions:
            create_question(db, source_id, question_data)
        print(f"Successfully saved {generated_count} questions to DB.")
    finally:
        db.close()
        
    # 【优化3】返回更详细的结果字典
    failures = total_requested - generated_count
    return {'generated': generated_count, 'failures': failures, 'total': total_requested, 'status': 'Task completed!'}