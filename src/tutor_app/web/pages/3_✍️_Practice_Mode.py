# src/tutor_app/web/pages/3_✍️_Practice_Mode.py
import streamlit as st
import json
import re
import time
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.db.models import KnowledgeSource, PracticeLog
from src.tutor_app.crud.crud_question import (
    get_question_batch_with_type_selection,
    get_questions_by_ids,
    get_review_questions,
    log_practice_and_update_srs
)
from src.tutor_app.tasks.grading import grade_short_answer_task
from src.tutor_app.crud.crud_question import create_log_for_grading
from src.tutor_app.web.components.task_monitor import display_global_task_monitor
from src.tutor_app.core.mock_data import get_mock_questions

# --- 页面配置与全局组件 ---
st.set_page_config(page_title="刷题模式", layout="wide")
display_global_task_monitor()

# --- 【新增】响应来自主页的“智能复习”指令 ---
if st.session_state.get("start_smart_review"):
    st.session_state.start_smart_review = False # 立即重置标志，防止重复触发
    
    db = SessionLocal()
    try:
        # 获取所有待复习题目
        review_questions = get_review_questions(db, count=999) # 获取所有待复习的
        if review_questions:
            type_order = ["单项选择题", "判断题", "填空题", "简答题"]
            st.session_state.session_questions = sorted(
                review_questions, 
                key=lambda q: type_order.index(q.question_type) if q.question_type in type_order else 99
            )
            st.session_state.current_q_index = 0
            st.session_state.user_answers = {}
            st.session_state.submitted_feedback = {}
            st.toast(f"已为您加载 {len(review_questions)} 道待复习题目！")
        else:
            st.toast("没有找到需要复习的题目。")
    finally:
        db.close()
    
    # 刷新页面以进入刷题界面
    st.rerun()

# --- Session State 初始化 ---
if 'session_questions' not in st.session_state: st.session_state.session_questions = []
if 'current_q_index' not in st.session_state: st.session_state.current_q_index = 0
if 'user_answers' not in st.session_state: st.session_state.user_answers = {}
if 'submitted_feedback' not in st.session_state: st.session_state.submitted_feedback = {}

# --- 核心业务逻辑与渲染函数 (无需修改) ---
def start_practice(mode, type_counts_dict, is_mock, source_ids=None):
    # ... (代码与上一版相同)
    questions = []
    if is_mock:
        questions = get_mock_questions(type_counts_dict)
        st.toast("已加载模拟数据！")
    else:
        db = SessionLocal()
        try:
            if mode == "🧠 智能复习":
                st.info("智能复习模式将根据您的记忆曲线推送题目。")
                questions = get_review_questions(db, count=sum(type_counts_dict.values()))
            else:
                if not source_ids:
                    st.error("请至少选择一个知识库！")
                    return
                questions = get_question_batch_with_type_selection(db, mode, type_counts_dict, source_ids)
        finally:
            db.close()
        st.toast(f"已从数据库加载 {len(questions)} 道题目！")
    
    if questions:
        type_order = ["单项选择题", "判断题", "填空题", "简答题"]
        st.session_state.session_questions = sorted(
            questions, 
            key=lambda q: type_order.index(q.question_type) if q.question_type in type_order else 99
        )
        st.session_state.current_q_index = 0
        st.session_state.user_answers = {}
        st.session_state.submitted_feedback = {}
        st.rerun()
    else:
        st.error(f"所选范围内没有找到符合条件的题目！")

def go_to_question(index):
    st.session_state.current_q_index = index

def submit_current_answer():
    # ... (代码与上一版相同)
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
            is_correct = False 
        elif question.question_type == "填空题":
            correct_answer_list = answer_data["blanks"]
            is_correct = (isinstance(user_answer, list) and len(user_answer) == len(correct_answer_list) and all(ua.strip().lower() == ca.strip().lower() for ua, ca in zip(user_answer, correct_answer_list)))
            correct_answer_display = ", ".join(correct_answer_list)
        
        st.session_state.submitted_feedback[q_id] = {
            'is_correct': is_correct, 
            'correct_answer': correct_answer_display,
            'user_answer_str': str(user_answer),
            'srs_recorded': False
        }
    except Exception as e:
        st.error(f"批改当前题目时出错: {e}")

def render_question_and_feedback_area(question):
    # ... (代码与上一版相同)
    q_id = question.id
    content = json.loads(question.content)
    is_submitted = q_id in st.session_state.submitted_feedback
    
    # 将题目和作答区域放在一个带边框的容器中
    with st.container(border=True):
        st.markdown(f"**题目ID: {q_id}** | **类型: {question.question_type}**")
        st.divider()
        
        st.write("") # 增加一点垂直间距
        
        if question.question_type in ["单项选择题", "判断题"]:
            st.write(f"#### {content['question']}")
            st.write("")
            options = content.get("options", ["正确", "错误"])
            current_answer = st.session_state.user_answers.get(q_id)
            index = options.index(current_answer) if current_answer in options else None
            user_choice = st.radio("请选择你的答案:", options, key=f"user_answer_{q_id}", index=index, horizontal=True, disabled=is_submitted)
            if user_choice: st.session_state.user_answers[q_id] = user_choice
        
        elif question.question_type == "简答题":
            st.write(f"#### {content['question']}")
            st.write("")
            user_text = st.text_area("请输入你的答案:", key=f"user_answer_{q_id}", value=st.session_state.user_answers.get(q_id, ""), height=150, disabled=is_submitted)
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
                    user_blanks[i] = st.text_input(f"填空 {i+1}", key=f"user_answer_{q_id}_{i}", value=user_blanks[i], disabled=is_submitted)
            st.session_state.user_answers[q_id] = user_blanks

    # 将所有反馈信息整合到另一个独立的容器中
    if is_submitted:
        st.write("") # 增加与上方题目的间距
        with st.container(border=True):
            feedback = st.session_state.submitted_feedback[q_id]
            
            if question.question_type != "简答题":
                if feedback['is_correct']: st.success(f"🎉 回答正确！")
                else: st.error(f"😔 回答错误。")
            
            st.info(f"**标准答案**: {feedback['correct_answer']}")
            if question.analysis:
                with st.expander("💡 查看题目解析"): st.info(question.analysis)

            st.divider()

            if question.question_type == "简答题":
                db = SessionLocal()
                log_entry = db.query(PracticeLog).filter(PracticeLog.id == feedback.get("log_id")).first()
                db.close()
                if log_entry and log_entry.ai_score:
                    st.subheader("🤖 AI 助教点评")
                    score_map = {"正确": "success", "部分正确": "warning", "错误": "error"}
                    score_type = score_map.get(log_entry.ai_score, "info")
                    getattr(st, score_type)(f"**评价: {log_entry.ai_score}**")
                    st.write(f"**评语:** {log_entry.ai_feedback}")
                elif "task_id" in feedback:
                    st.info("🤖 AI 助教正在批阅您的答案，请稍后...")
                else:
                    if st.button("请求 AI 辅助评分", key=f"grade_{q_id}", use_container_width=True):
                        with st.spinner("正在提交给AI助教..."):
                            db_session = SessionLocal()
                            try:
                                log_id = create_log_for_grading(db_session, q_id, feedback['user_answer_str'])
                                st.session_state.submitted_feedback[q_id]["log_id"] = log_id
                                task = grade_short_answer_task.delay(log_id)
                                st.session_state.submitted_feedback[q_id]["task_id"] = task.id
                                st.rerun()
                            finally:
                                db_session.close()
            else:
                if not feedback.get('srs_recorded'):
                    st.write("**请评价您对这道题的掌握程度：**")
                    def record_srs_feedback(q_id, quality):
                        feedback_data = st.session_state.submitted_feedback[q_id]
                        db = SessionLocal()
                        try:
                            log_practice_and_update_srs(db, question_id=q_id, is_correct=feedback_data['is_correct'], quality=quality, user_answer=feedback_data['user_answer_str'])
                            st.session_state.submitted_feedback[q_id]['srs_recorded'] = True
                            st.toast("记忆状态已更新！")
                            time.sleep(0.5)
                            st.rerun()
                        finally:
                            db.close()
                    cols = st.columns(4)
                    cols[0].button("😭 完全忘记", key=f"srs_{q_id}_0", on_click=record_srs_feedback, args=(q_id, 0), use_container_width=True)
                    cols[1].button("🤔 有点模糊", key=f"srs_{q_id}_3", on_click=record_srs_feedback, args=(q_id, 3), use_container_width=True)
                    cols[2].button("🙂 掌握了", key=f"srs_{q_id}_4", on_click=record_srs_feedback, args=(q_id, 4), use_container_width=True)
                    cols[3].button("😎 非常简单", key=f"srs_{q_id}_5", on_click=record_srs_feedback, args=(q_id, 5), use_container_width=True, type="primary")
                else:
                    st.success("✔️ 您的记忆反馈已记录。")

# --- 页面主逻辑 ---
st.title("✍️ 刷题练习模式")

# --- 视图1: 练习设置界面 (修正版) ---
if not st.session_state.session_questions:
    st.sidebar.header("开发设置")
    MOCK_MODE = st.sidebar.toggle("🧪 使用模拟数据", value=False)
    
    with st.container(border=True):
        st.header("开始新的练习")

        # --- 【核心修正】将动态组件移出 st.form ---
        
        with st.expander("**第一步: 选择学习资料和模式**", expanded=True):
            db = SessionLocal()
            completed_sources = db.query(KnowledgeSource).filter(KnowledgeSource.status == 'completed').all()
            source_options = {f"{s.id}: {s.filename}": s.id for s in completed_sources}
            db.close()
            selected_source_names = st.multiselect("选择题目来源 (可多选):", options=list(source_options.keys()), default=list(source_options.keys()) if source_options else [])
            selected_source_ids = [source_options[name] for name in selected_source_names]
            mode = st.radio("选择刷题模式:", ("混合模式", "只刷新题", "只刷错题", "🧠 智能复习"), horizontal=True, help="智能复习会根据记忆曲线推送题目，将忽略上方知识库选择。")
        
        with st.expander("**第二步: 配置题型和数量**", expanded=True):
            available_types = ["单项选择题", "判断题", "填空题", "简答题"]
            # 我们为多选框设置一个 key，以便在表单外也能稳定地访问它的状态
            selected_types = st.multiselect("选择要练习的题型:", options=available_types, default=["单项选择题", "判断题"], key="practice_selected_types")
            
            type_counts = {}
            if selected_types:
                # 动态生成列和数字输入框的逻辑现在可以正常工作了
                cols = st.columns(len(selected_types))
                for i, q_type in enumerate(selected_types):
                    with cols[i]:
                        type_counts[q_type] = st.number_input(f"“{q_type}”数量:", min_value=1, max_value=50, value=5, key=f"num_{q_type}")
        
        st.divider()

        # --- 【核心修正】st.form 现在只包裹提交按钮 ---
        with st.form("start_practice_form"):
            submitted = st.form_submit_button("🚀 开始练习", type="primary", use_container_width=True)
            if submitted:
                # 在提交时，我们从 session_state 或直接从变量中获取最新的值
                final_selected_types = st.session_state.practice_selected_types
                final_type_counts = {}
                # 重新构建一次 type_counts 确保数据是提交时的最终状态
                for q_type in final_selected_types:
                    # Streamlit 会自动通过 key 保存每个 number_input 的值
                    final_type_counts[q_type] = st.session_state[f"num_{q_type}"]

                if not final_type_counts:
                    st.error("请至少选择一种题型并设置数量！")
                else:
                    # 使用捕获到的最终数据来启动练习
                    start_practice(mode, final_type_counts, MOCK_MODE, selected_source_ids)
# --- 视图2: 刷题主界面 (最终美化版) ---
else:
    q_index = st.session_state.current_q_index
    total_questions = len(st.session_state.session_questions)
    current_question = st.session_state.session_questions[q_index]
    is_submitted = current_question.id in st.session_state.submitted_feedback

    # ---【UI优化1: 调整主布局比例为2:1】---
    col1, col2 = st.columns([2, 1], gap="large")
    
    with col1:
        # ---【UI优化2: 重构顶部控制栏】---
        st.subheader(f"题目 {q_index + 1} / {total_questions}")
        st.progress((q_index + 1) / total_questions, text="") # 进度条更简洁
        
        # 将操作按钮放在进度条下方，更清晰
        nav_cols = st.columns(3)
        with nav_cols[0]:
            st.button("⏮️ 上一题", use_container_width=True, disabled=(q_index == 0), on_click=go_to_question, args=(q_index - 1,))
        with nav_cols[1]:
            st.button("✅ 提交本题答案", type="primary", use_container_width=True, disabled=is_submitted, on_click=submit_current_answer)
        with nav_cols[2]:
            st.button("下一题 ⏭️", use_container_width=True, disabled=(q_index == total_questions - 1), on_click=go_to_question, args=(q_index + 1,))
        
        st.write("") # 增加垂直间距
        render_question_and_feedback_area(current_question)

    with col2:
        with st.container(border=True):
            st.header("📊 练习状态")
            total_submitted = len(st.session_state.submitted_feedback)
            correct_submitted = sum(1 for feedback in st.session_state.submitted_feedback.values() if feedback['is_correct'])
            accuracy = (correct_submitted / total_submitted * 100) if total_submitted > 0 else 0
            
            # 使用列来美化指标显示
            metric_cols = st.columns(2)
            metric_cols[0].metric("已提交", f"{total_submitted}/{total_questions}")
            metric_cols[1].metric("正确率", f"{accuracy:.1f}%")
            
            st.divider() # 使用分隔线
            
            st.subheader("💡 智能答题卡")
            st.write("") # 增加一点垂直间距
            
            QUESTIONS_PER_ROW = 8
            num_rows = (total_questions + QUESTIONS_PER_ROW - 1) // QUESTIONS_PER_ROW
            
            for row_index in range(num_rows):
                cols = st.columns(QUESTIONS_PER_ROW)
                start_index = row_index * QUESTIONS_PER_ROW
                end_index = min(start_index + QUESTIONS_PER_ROW, total_questions)

                for i in range(start_index, end_index):
                    q = st.session_state.session_questions[i]
                    col_index = i % QUESTIONS_PER_ROW
                    with cols[col_index]:
                        q_id = q.id
                        btn_label = f"{i+1}"
                        help_text = f"题目 {i+1} ({q.question_type})"
                        btn_type = "primary" if i == q_index else "secondary"
                        
                        if q_id in st.session_state.submitted_feedback:
                            feedback = st.session_state.submitted_feedback[q_id]
                            if q.question_type != "简答题":
                                is_correct = feedback['is_correct']
                                btn_label = "✅" if is_correct else "❌"
                                help_text += " - 正确" if is_correct else " - 错误"
                            else:
                                 btn_label = "✍️"
                                 help_text += " - 已作答"
                        
                        st.button(btn_label, key=f"jump_{i}", use_container_width=True, help=help_text, on_click=go_to_question, args=(i,), type=btn_type)
        
        st.write("")
        if st.button("🔚 结束本次练习", use_container_width=True, type="secondary", key="finish_practice"):
            st.session_state.session_questions = []
            st.rerun()