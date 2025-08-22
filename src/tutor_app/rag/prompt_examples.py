# src/tutor_app/rag/prompt_examples.py

# 这里存放高质量的出题范例，用于“教”会AI如何出题
# 每个范例都包含了上下文、用户请求和AI应返回的理想JSON

FEW_SHOT_EXAMPLES = [
    {
        "context": "Python的内置数据结构包括列表(list)、元组(tuple)、字典(dict)和集合(set)。列表是可变的有序序列，而元组是不可变的有序序列。",
        "question_type": "单项选择题",
        "output": """
        {
            "question_type": "单项选择题",
            "content": {
                "question": "在Python中，哪种数据结构是不可变的有序序列？",
                "options": [
                    "A. 列表 (list)",
                    "B. 字典 (dict)",
                    "C. 集合 (set)",
                    "D. 元组 (tuple)"
                ]
            },
            "answer": {
                "correct_option_index": 3
            },
            "analysis": "根据上下文，列表是可变的，而元组是不可变的有序序列。",
            "knowledge_tag": "Python数据结构"
        }
        """
    },
    {
        "context": "Alembic是SQLAlchemy的官方数据库迁移工具，它允许开发者追踪数据库模式的变化，并通过迁移脚本来应用这些变更。",
        "question_type": "判断题",
        "output": """
        {
            "question_type": "判断题",
            "content": {
                "question": "Alembic是Django框架自带的数据库迁移工具。"
            },
            "answer": {
                "correct_answer": false
            },
            "analysis": "根据上下文，Alembic是SQLAlchemy的官方工具，而不是Django自带的。",
            "knowledge_tag": "Alembic数据库迁移"
        }
        """
    },
]