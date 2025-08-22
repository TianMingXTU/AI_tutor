# src/tutor_app/rag/json_parser.py

import json
import re
from typing import Optional, Dict
from src.tutor_app.llms.llm_factory import get_chat_model

def extract_json_from_text(text: str) -> Optional[str]:
    """
    【升级版】使用正则表达式从文本中提取最可能是一个完整JSON对象的部分。
    """
    # 优先匹配被```json ... ```包裹的内容
    match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text)
    if match:
        return match.group(1)
    
    # 如果没有，则寻找第一个'{'和最后一个'}'之间的内容
    start_index = text.find('{')
    end_index = text.rfind('}')
    if start_index != -1 and end_index != -1 and end_index > start_index:
        return text[start_index : end_index + 1]
            
    return None

def remove_trailing_commas(json_string: str) -> str:
    """
    使用正则表达式移除JSON中多余的结尾逗号。
    """
    # 移除在 } 或 ] 之前的多余逗号
    json_string = re.sub(r',\s*([\}\]])', r'\1', json_string)
    return json_string

def repair_json_with_llm(broken_json_string: str) -> str:
    """
    【升级版】使用一个带有更强力Prompt的大模型来修复损坏的JSON字符串。
    """
    print("  [Parser Stage 4] 常规和程序化修复失败，启动AI终极修复...")
    llm = get_chat_model()
    
    prompt = f"""
    你是一个JSON格式修复专家。你的唯一任务是分析下面提供的、已损坏的文本，并返回一个语法完全正确的JSON对象。
    
    ## 严格要求：
    1.  你的输出**必须**是一个完整的、可以被任何标准解析器成功解析的JSON对象。
    2.  **不要**在JSON前后添加任何解释、说明或Markdown标记（如```json）。
    3.  你的输出**必须**以`{{`开头，并以`}}`结尾。
    4.  修复常见的错误，如缺失的引号、括号不匹配、错误的转义符和多余的逗号。

    ## 已损坏的JSON文本:
    ```
    {broken_json_string}
    ```

    ## 请输出修复后的JSON:
    """
    
    try:
        repaired_string = llm.invoke(prompt)
        return repaired_string
    except Exception as e:
        print(f"  [Parser Stage 4] AI修复JSON时出错: {e}")
        return broken_json_string

def parse_json_with_ai_fallback(llm_output: str) -> Optional[Dict]:
    """
    【全新四级火箭】一个极其健壮的JSON解析器，具备多重降级修复功能。
    """
    if not llm_output or not isinstance(llm_output, str):
        return None

    # --- 第一级：智能提取 ---
    print("  [Parser Stage 1] 正在提取JSON...")
    json_string = extract_json_from_text(llm_output)
    if not json_string:
        print(f"  [Parser Stage 1] 失败: 在文本中未找到JSON对象。")
        return None

    # --- 第二级：标准解析 ---
    try:
        print("  [Parser Stage 2] 正在尝试标准解析...")
        return json.loads(json_string)
    except json.JSONDecodeError:
        print(f"  [Parser Stage 2] 失败: 标准解析失败。")

    # --- 第三级：程序化修复 (移除结尾逗号) ---
    try:
        print("  [Parser Stage 3] 正在尝试程序化修复 (移除结尾逗号)...")
        fixed_string = remove_trailing_commas(json_string)
        return json.loads(fixed_string)
    except json.JSONDecodeError:
        print(f"  [Parser Stage 3] 失败: 程序化修复后解析仍然失败。")

    # --- 第四级：AI终极修复 ---
    repaired_by_ai_string = repair_json_with_llm(json_string)
    final_json_string = extract_json_from_text(repaired_by_ai_string)
    
    if not final_json_string:
        print(f"  [Parser Stage 4] 失败: AI修复后未能提取出JSON。")
        return None

    try:
        return json.loads(final_json_string)
    except json.JSONDecodeError as e:
        print(f"  [Parser Stage 4] 失败: AI终极修复后仍然解析失败。最终错误: {e}")
        print(f"  [Parser Stage 4] 失败的JSON文本: {final_json_string}")
        return None