# src/tutor_app/schemas/question.py

from pydantic import BaseModel, Field
from typing import List, Dict, Union

# --- 单项选择题的结构 ---
class MultipleChoiceContent(BaseModel):
    question: str = Field(description="题目的主要文本内容")
    options: List[str] = Field(description="四个选项的字符串列表，例如 ['A. ...', 'B. ...', 'C. ...', 'D. ...']")

class MultipleChoiceAnswer(BaseModel):
    correct_option_index: int = Field(description="正确选项在options列表中的索引，从0开始 (0, 1, 2, 或 3)")

class MultipleChoiceQuestionSchema(BaseModel):
    question_type: str = Field(description="题目类型, 固定为 '单项选择题'")
    content: MultipleChoiceContent
    answer: MultipleChoiceAnswer
    analysis: str = Field(description="对题目和答案的详细解析")
    knowledge_tag: str = Field(description="该题目所属的核心知识点或标签")

# --- 判断题的结构 ---
class TrueFalseContent(BaseModel):
    question: str = Field(description="需要判断对错的题干")

class TrueFalseAnswer(BaseModel):
    correct_answer: bool = Field(description="正确答案，true代表“正确”，false代表“错误”")

class TrueFalseQuestionSchema(BaseModel):
    question_type: str = Field(description="题目类型, 固定为 '判断题'")
    content: TrueFalseContent
    answer: TrueFalseAnswer
    analysis: str = Field(description="对题目和答案的详细解析")
    knowledge_tag: str = Field(description="该题目所属的核心知识点或标签")

# --- 简答题的结构 ---
class ShortAnswerContent(BaseModel):
    question: str = Field(description="需要用文字回答的题干")

class ShortAnswerAnswer(BaseModel):
    text: str = Field(description="该问题的参考答案或标准答案")

class ShortAnswerQuestionSchema(BaseModel):
    question_type: str = Field(description="题目类型, 固定为 '简答题'")
    content: ShortAnswerContent
    answer: ShortAnswerAnswer
    analysis: str = Field(description="对答案的评分要点或详细解析")
    knowledge_tag: str = Field(description="该题目所属的核心知识点或标签")

# src/tutor_app/schemas/question.py

# ... (保留已有的 MultipleChoice, TrueFalse, ShortAnswer 的Schema) ...

# --- 填空题的结构 ---
class FillInTheBlankContent(BaseModel):
    # 我们用 "___" (三个下划线) 作为题干中的占位符
    stem: str = Field(description="包含一个或多个'___'占位符的题干文本")

class FillInTheBlankAnswer(BaseModel):
    blanks: List[str] = Field(description="一个字符串列表，按顺序包含每个占位符的正确答案")

class FillInTheBlankQuestionSchema(BaseModel):
    question_type: str = Field(description="题目类型, 固定为 '填空题'")
    content: FillInTheBlankContent
    answer: FillInTheBlankAnswer
    analysis: str = Field(description="对题目和答案的详细解析")
    knowledge_tag: str = Field(description="该题目所属的核心知识点或标签")