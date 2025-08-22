# src/tutor_app/web/pages/3_✍️_Practice_Mode.py
import streamlit as st
import json
import re
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.db.models import KnowledgeSource  # 添加 KnowledgeSource 的导入
# 【新增】导入 get_questions_by_ids
from src.tutor_app.crud.crud_question import get_question_batch_by_mode, create_practice_log, get_questions_by_ids
from src.tutor_app.core.mock_data import get_mock_questions

st.set_page_config(page_title="刷题模式", layout="wide")

# --- 【核心优化】增加“错题集训”启动逻辑 ---
if "practice_from_mistakes" in st.session_state and st.session_state.practice_from_mistakes:
    mistake_ids = st.session_state.practice_from_mistakes
    # 清理掉这个“指令”，防止下次刷新时重复执行
    st.session_state.practice_from_mistakes = None

    db = SessionLocal()
    questions = get_questions_by_ids(db, mistake_ids)
    db.close()
    
    if questions:
        st.session_state.session_questions = questions
        st.session_state.current_q_index = 0
        st.session_state.user_answers = {}
        st.session_state.submitted_feedback = {}
        st.toast("错题集训开始！")
    else:
        st.error("加载错题失败！")

# --- Session State & Callback Functions (保持不变) ---
# ... (文件的其余所有部分都保持不变)

# --- Session State & Callback Functions ---
if 'session_questions' not in st.session_state: st.session_state.session_questions = []
if 'current_q_index' not in st.session_state: st.session_state.current_q_index = 0
if 'user_answers' not in st.session_state: st.session_state.user_answers = {}
if 'submitted_feedback' not in st.session_state: st.session_state.submitted_feedback = {}

def start_practice(mode, type_counts_dict, is_mock, source_ids=None):
    if not type_counts_dict:
        st.error("请至少选择一种题型并设置数量！")
        return

    questions = []
    if is_mock:
        questions = get_mock_questions(type_counts_dict)
        st.toast("已加载模拟数据！")
    else:
        if not source_ids:
            st.error("真实刷题模式下，请至少选择一个知识库！")
            return
        db = SessionLocal()
        questions = get_question_batch_by_mode(db, mode, type_counts_dict, source_ids)
        db.close()
        st.toast(f"已从数据库加载题目！")
    
    if questions:
        type_order = ["单项选择题", "判断题", "填空题", "简答题"]
        st.session_state.session_questions = sorted(
            questions, 
            key=lambda q: type_order.index(q.question_type) if q.question_type in type_order else 99
        )
        st.session_state.current_q_index = 0
        st.session_state.user_answers = {}
        st.session_state.submitted_feedback = {}
    else:
        st.error(f"所选范围内没有找到符合条件的题目！")

def go_to_question(index):
    st.session_state.current_q_index = index

def submit_current_answer(is_mock):
    q_index = st.session_state.current_q_index
    question = st.session_state.session_questions[q_index]
    q_id = question.id
    user_answer = st.session_state.user_answers.get(q_id)
    if user_answer is None or (isinstance(user_answer, list) and not any(ans.strip() for ans in user_answer)):
        st.warning("请先作答后再提交！")
        return
    is_correct = False
    correct_answer_display = ""
    try:
        answer_data = json.loads(question.answer)
        content_data = json.loads(question.content)
        if question.question_type == "单项选择题":
            correct_answer_display = content_data["options"][answer_data["correct_option_index"]]
            is_correct = (user_answer == correct_answer_display)
        elif question.question_type == "判断题":
            correct_answer_display = "正确" if answer_data["correct_answer"] else "错误"
            is_correct = (user_answer == correct_answer_display)
        elif question.question_type == "简答题":
            correct_answer_display = answer_data["text"]
            is_correct = (user_answer.strip() == correct_answer_display.strip())
        elif question.question_type == "填空题":
            correct_answer_list = answer_data["blanks"]
            is_correct = (isinstance(user_answer, list) and len(user_answer) == len(correct_answer_list) and all(ua.strip() == ca.strip() for ua, ca in zip(user_answer, correct_answer_list)))
            correct_answer_display = ", ".join(correct_answer_list)
        st.session_state.submitted_feedback[q_id] = {'is_correct': is_correct, 'correct_answer': correct_answer_display}
        if not is_mock:
            db = SessionLocal()
            create_practice_log(db, q_id, str(user_answer), is_correct)
            db.close()
    except Exception as e:
        print(f"Error during submission for question ID {q_id}: {e}")
        st.error("批改当前题目时出错。")

def render_question_area(question):
    q_id = question.id
    content = json.loads(question.content)
    is_disabled = q_id in st.session_state.submitted_feedback
    with st.container(border=True):
        st.markdown(f"**题目ID: {q_id}** | **类型: {question.question_type}**")
        st.divider()
        if question.question_type in ["单项选择题", "判断题"]:
            st.write(f"#### {content['question']}")
            options = content.get("options", ["正确", "错误"])
            current_answer = st.session_state.user_answers.get(q_id)
            index = options.index(current_answer) if current_answer in options else None
            user_choice = st.radio("请选择你的答案:", options, key=f"user_answer_{q_id}", index=index, horizontal=True, disabled=is_disabled)
            if user_choice: st.session_state.user_answers[q_id] = user_choice
        elif question.question_type == "简答题":
            st.write(f"#### {content['question']}")
            user_text = st.text_area("请输入你的答案:", key=f"user_answer_{q_id}", value=st.session_state.user_answers.get(q_id, ""), disabled=is_disabled)
            if user_text: st.session_state.user_answers[q_id] = user_text
        elif question.question_type == "填空题":
            stem = content["stem"]
            num_blanks = stem.count("___")
            display_stem = re.sub(r'___', lambda m, c=iter(range(1, num_blanks + 1)): f"__({next(c)})__", stem)
            st.markdown(f"#### {display_stem}")
            st.divider()
            user_blanks = st.session_state.user_answers.get(q_id, [""] * num_blanks)
            cols = st.columns(num_blanks or 1)
            for i in range(num_blanks):
                with cols[i]:
                    user_blanks[i] = st.text_input(f"填空 {i+1}", key=f"user_answer_{q_id}_{i}", value=user_blanks[i], disabled=is_disabled)
            st.session_state.user_answers[q_id] = user_blanks
        if q_id in st.session_state.submitted_feedback:
            feedback = st.session_state.submitted_feedback[q_id]
            if feedback['is_correct']:
                st.success(f"🎉 回答正确！正确答案是: **{feedback['correct_answer']}**")
            else:
                st.error(f"😔 回答错误。正确答案是: **{feedback['correct_answer']}**")
            if question.analysis:
                with st.expander("💡 查看题目解析"): st.info(question.analysis)

# --- 页面主逻辑 ---
st.title("刷题模式")
st.sidebar.header("开发设置")
MOCK_MODE = st.sidebar.toggle("🧪 使用模拟数据", value=True)

if not st.session_state.session_questions:
    with st.container(border=True):
        st.header("开始新的练习")
        
        db = SessionLocal()
        completed_sources = db.query(KnowledgeSource).filter(KnowledgeSource.status == 'completed').all()
        source_options = {f"{s.id}: {s.filename}": s.id for s in completed_sources}
        db.close()

        # --- 【核心功能】知识库筛选器 ---
        selected_source_names = st.multiselect(
            "选择题目来源的知识库 (可多选):",
            options=list(source_options.keys()),
            default=list(source_options.keys()) if source_options else []
        )
        selected_source_ids = [source_options[name] for name in selected_source_names]
        
        st.write("---")
        mode = st.radio("选择刷题模式:", ("混合模式", "只刷新题", "只刷错题"), horizontal=True)
        
        st.subheader("选择题型和数量")
        available_types = ["单项选择题", "判断题", "填空题", "简答题"]
        selected_types = st.multiselect(
            "请选择要练习的题型:",
            options=available_types,
            default=["单项选择题", "判断题"]
        )
        
        type_counts = {}
        if selected_types:
            cols = st.columns(len(selected_types))
            for i, q_type in enumerate(selected_types):
                with cols[i]:
                    type_counts[q_type] = st.number_input(
                        f"“{q_type}”数量:",
                        min_value=1, max_value=50, value=5, key=f"num_{q_type}"
                    )
        
        st.divider()
        st.button(
            "开始练习", 
            type="primary", 
            use_container_width=True, 
            on_click=start_practice, 
            args=(mode, type_counts, MOCK_MODE, selected_source_ids)
        )
else:
    col1, col2 = st.columns([3, 1])
    q_index = st.session_state.current_q_index
    total_questions = len(st.session_state.session_questions)
    current_question = st.session_state.session_questions[q_index]

    with col1:
        st.progress((q_index + 1) / total_questions, text=f"进度: {q_index + 1} / {total_questions}")
        render_question_area(current_question)
        st.divider()
        nav_cols = st.columns([1, 1, 2])
        with nav_cols[0]:
            st.button("⏮️ 上一题", use_container_width=True, disabled=(q_index == 0), on_click=go_to_question, args=(q_index - 1,))
        with nav_cols[1]:
            st.button("下一题 ⏭️", use_container_width=True, disabled=(q_index == total_questions - 1), on_click=go_to_question, args=(q_index + 1,))
        with nav_cols[2]:
            st.button("提交本题", type="primary", use_container_width=True, disabled=(current_question.id in st.session_state.submitted_feedback), on_click=submit_current_answer, args=(MOCK_MODE,))

    with col2:
        st.header("📊 练习状态")
        total_submitted = len(st.session_state.submitted_feedback)
        correct_submitted = sum(1 for feedback in st.session_state.submitted_feedback.values() if feedback['is_correct'])
        accuracy = (correct_submitted / total_submitted * 100) if total_submitted > 0 else 0
        st.metric("已提交 / 总题数", f"{total_submitted} / {total_questions}")
        st.metric("正确率", f"{accuracy:.1f}%")
        st.divider()
        st.subheader("智能答题卡")
        cols = st.columns(12) 
        for i, q in enumerate(st.session_state.session_questions):
            col = cols[i % 12]
            with col:
                q_id_map = q.id
                if q_id_map in st.session_state.submitted_feedback:
                    is_correct = st.session_state.submitted_feedback[q_id_map]['is_correct']
                    label = "✅" if is_correct else "❌"
                    st.button(label, key=f"jump_{i}", use_container_width=True, help=f"题目 {i+1}", on_click=go_to_question, args=(i,))
                else:
                    btn_type = "primary" if i == q_index else "secondary"
                    st.button(f"{i+1}", key=f"jump_{i}", use_container_width=True, type=btn_type, on_click=go_to_question, args=(i,))
        
        if st.button("结束本次练习", use_container_width=True, type="secondary"):
            st.session_state.session_questions = []
            st.rerun()