# src/tutor_app/core/mock_data.py
import json
import datetime
from typing import Dict

class MockQuestion:
    """一个模拟SQLAlchemy Question对象的类。"""
    def __init__(self, id, question_type, content, answer, analysis):
        self.id = id
        self.question_type = question_type
        self.content = json.dumps(content)
        self.answer = json.dumps(answer)
        self.analysis = analysis
        self.created_at = datetime.datetime.utcnow()

# 我们创建一个更大、包含各种题型的“模拟题库”
FULL_MOCK_POOL = [
    MockQuestion(
        id=101, question_type="单项选择题",
        content={"question": "在Python中，哪个关键字用于定义一个函数？", "options": ["A. func", "B. def", "C. function", "D. define"]},
        answer={"correct_option_index": 1},
        analysis="`def` 是 Python 中用于定义函数的关键字。"
    ),
    MockQuestion(
        id=102, question_type="判断题",
        content={"question": "Streamlit 是一个后端框架，类似于Django。"},
        answer={"correct_answer": False},
        analysis="Streamlit 主要是一个用于快速构建数据应用的前端框架。"
    ),
    MockQuestion(
        id=103, question_type="简答题",
        content={"question": "请简述什么是 RAG (Retrieval-Augmented Generation)？"},
        answer={"text": "RAG是一种结合了检索和生成的人工智能模型架构，它先检索相关信息，再根据信息生成回答。"},
        analysis="核心在于“先检索，后生成”，解决了大模型知识更新不及时和容易产生幻觉的问题。"
    ),
    MockQuestion(
        id=104, question_type="单项选择题",
        content={"question": "Celery 使用哪个工具作为默认的消息中间件（Broker）？", "options": ["A. Kafka", "B. PostgreSQL", "C. RabbitMQ", "D. SQLite"]},
        answer={"correct_option_index": 2},
        analysis="Celery 最初是为 RabbitMQ 设计的，并将其作为最稳定和功能最全的 Broker 推荐。"
    ),
    MockQuestion(
        id=105, question_type="填空题",
        content={"stem": "Ollama是一个能让您在本地运行___和___等大语言模型的工具。"},
        answer={"blanks": ["Llama 2", "Mistral"]},
        analysis="Ollama支持多种主流的开源大语言模型。"
    ),
    MockQuestion(
        id=106, question_type="判断题",
        content={"question": "在Python中，列表（List）是不可变的数据类型。"},
        answer={"correct_answer": False},
        analysis="列表（List）是可变的（mutable），而元组（Tuple）是不可变的（immutable）。"
    ),
]

def get_mock_questions(type_counts: Dict[str, int]):
    """
    【全新升级版】根据用户选择的题型和数量，精确地从模拟题库中提取题目。
    """
    output_questions = []
    # 按照预设的题型顺序来提取，确保最终输出的题目也是有序的
    type_order = ["单项选择题", "判断题", "填空题", "简答题"]

    for q_type in type_order:
        if q_type in type_counts:
            count = type_counts[q_type]
            # 从题库中筛选出所有符合当前类型的题目
            filtered_by_type = [q for q in FULL_MOCK_POOL if q.question_type == q_type]
            
            # 为了防止数量不够，循环从筛选出的题目中提取
            for i in range(count):
                if filtered_by_type:
                    # 使用取模运算循环获取，确保不会因数量不足而报错
                    question_to_add = filtered_by_type[i % len(filtered_by_type)]
                    # 创建一个新的实例，并赋予唯一的ID，防止Streamlit因key重复而出错
                    new_q = MockQuestion(
                        id=f"{question_to_add.id}_{i}", # 关键：创建唯一ID
                        question_type=question_to_add.question_type,
                        content=json.loads(question_to_add.content),
                        answer=json.loads(question_to_add.answer),
                        analysis=question_to_add.analysis
                    )
                    output_questions.append(new_q)
    
    return output_questions