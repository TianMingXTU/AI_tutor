# src/tutor_app/rag/question_generator.py

from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_chroma import Chroma
from src.tutor_app.llms.llm_factory import get_chat_model, get_embedding_model
from src.tutor_app.rag.knowledge_base import CHROMA_PERSIST_DIRECTORY
from .prompt_examples import FEW_SHOT_EXAMPLES

def get_questions_chain(question_type: str, source_id: int):
    """
    【同步版】构建一个使用“少样本”提示的RAG链。
    """
    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "上下文知识:\n---\n{context}\n---\n请生成一道“{question_type}”题目。"),
            ("ai", "{output}"),
        ]
    )
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=FEW_SHOT_EXAMPLES,
        input_variables=["context", "question_type"],
    )
    final_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是一名教学经验丰富的出题专家。请严格模仿范例的JSON格式进行输出。"),
            few_shot_prompt,
            ("human", "上下文知识:\n---\n{context}\n---\n请生成一道“{question_type}”题目。"),
        ]
    )
    vectorstore = Chroma(
        persist_directory=CHROMA_PERSIST_DIRECTORY,
        embedding_function=get_embedding_model()
    )
    retriever = vectorstore.as_retriever(
        search_kwargs={'filter': {'source_id': str(source_id)}}
    )
    llm = get_chat_model()
    rag_chain = (
        {"context": retriever, "question_type": RunnablePassthrough()}
        | final_prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain