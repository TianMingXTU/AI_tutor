# src/tutor_app/tasks/grading.py
import json
from .celery_app import celery_app
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.db.models import PracticeLog, Question
from src.tutor_app.llms.llm_factory import get_chat_model
from src.tutor_app.rag.json_parser import parse_json_with_ai_fallback

GRADING_PROMPT_TEMPLATE = """
你是一名经验丰富、公平公正的AI助教。你的任务是根据提供的“标准答案”，评估“用户的回答”是否正确地回答了“原始问题”。

## 规则：
1.  **精确性优先**: 严格依据“标准答案”的核心要点来评判。
2.  **理解意图**: 即使用户的措辞不同，只要核心意思正确，也应给予肯定。
3.  **输出格式**: 你的回答必须是一个严格的JSON对象，包含两个字段：`score` 和 `feedback`。
    * `score`: 必须是以下三个字符串之一: "正确", "部分正确", "错误"。
    * `feedback`: 对你的评分给出简明扼要的解释（50字以内）。

## 评估材料：
### 原始问题:
{question}

### 标准答案:
{standard_answer}

### 用户的回答:
{user_answer}

## 请输出你的JSON格式评估结果:
"""

@celery_app.task(bind=True)
def grade_short_answer_task(self, log_id: int):
    """
    一个Celery任务，用于在后台对简答题进行AI评分。
    """
    db = SessionLocal()
    try:
        log_entry = db.query(PracticeLog).filter(PracticeLog.id == log_id).first()
        if not log_entry:
            raise ValueError("Log entry not found")
        
        question = db.query(Question).filter(Question.id == log_entry.question_id).first()
        if not question:
            raise ValueError("Question not found")
            
        question_content = json.loads(question.content)
        standard_answer = json.loads(question.answer)

        prompt = GRADING_PROMPT_TEMPLATE.format(
            question=question_content.get("question"),
            standard_answer=standard_answer.get("text"),
            user_answer=log_entry.user_answer
        )
        
        llm = get_chat_model()
        llm_output = llm.invoke(prompt)
        
        parsed_result = parse_json_with_ai_fallback(llm_output)
        
        if parsed_result and 'score' in parsed_result and 'feedback' in parsed_result:
            log_entry.ai_score = parsed_result['score']
            log_entry.ai_feedback = parsed_result['feedback']
            db.commit()
            return f"Success: Graded log {log_id}"
        else:
            log_entry.ai_feedback = "AI返回格式错误，无法解析评分。"
            db.commit()
            raise ValueError("AI response parsing failed")

    except Exception as e:
        self.update_state(state='FAILURE', meta={'exc': str(e)})
        db.rollback()
        return f"Failed to grade log {log_id}: {e}"
    finally:
        db.close()