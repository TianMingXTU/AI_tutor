# src/tutor_app/web/pages/4_📝_Mock_Exam.py
import streamlit as st
import json
import time
import re
from datetime import timedelta
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.db.models import KnowledgeSource
from src.tutor_app.crud.crud_question import get_question_batch_with_type_selection, save_exam_and_get_id, save_exam_result

st.set_page_config(page_title="模拟考试", layout="wide")
st.title("📝 模拟考试模式")

def question_to_dict(q):
    return {"id": q.id, "question_type": q.question_type, "content": q.content, "answer": q.answer, "analysis": q.analysis}

if 'exam_state' not in st.session_state: st.session_state.exam_state = "setup"
if 'exam_questions' not in st.session_state: st.session_state.exam_questions = []
if 'exam_id' not in st.session_state: st.session_state.exam_id = None
if 'exam_result' not in st.session_state: st.session_state.exam_result = None
if 'exam_end_time' not in st.session_state: st.session_state.exam_end_time = None

if st.session_state.exam_state == "setup":
    with st.container(border=True):
        st.header("考试设置")
        db = SessionLocal()
        completed_sources = db.query(KnowledgeSource).filter(KnowledgeSource.status == 'completed').all()
        
        if completed_sources:
            source_options = {f"{s.id}: {s.filename}": s.id for s in completed_sources}
            
            selected_source_names = st.multiselect(
                "请选择考试范围 (可多选知识库):",
                options=list(source_options.keys()),
                default=list(source_options.keys())[0] if source_options else []
            )
            selected_source_ids = [source_options[name] for name in selected_source_names]

            st.subheader("配置试卷题型和数量")
            available_types = ["单项选择题", "判断题", "填空题", "简答题"]
            selected_types = st.multiselect("请选择试卷包含的题型:", options=available_types, default=["单项选择题", "判断题"])
            type_counts = {}
            if selected_types:
                cols = st.columns(len(selected_types))
                for i, q_type in enumerate(selected_types):
                    with cols[i]:
                        type_counts[q_type] = st.number_input(f"“{q_type}”数量:", min_value=1, max_value=50, value=5, key=f"exam_num_{q_type}")
            
            total_q_count = sum(type_counts.values()) if type_counts else 0
            exam_duration_minutes = st.number_input("设置考试时长（分钟）:", min_value=1, value=int(total_q_count * 1.5))
            st.divider()

            if st.button("生成试卷并开始考试", type="primary", use_container_width=True):
                if selected_source_ids and type_counts:
                    questions_from_db = get_question_batch_with_type_selection(db, "混合模式", type_counts, selected_source_ids)
                    
                    if questions_from_db:
                        type_order = ["单项选择题", "判断题", "填空题", "简答题"]
                        sorted_questions = sorted(questions_from_db, key=lambda q: type_order.index(q.question_type))
                        st.session_state.exam_questions = [question_to_dict(q) for q in sorted_questions]
                        question_ids = [q['id'] for q in st.session_state.exam_questions]
                        exam_title = f"综合考试: {', '.join(selected_source_names)}"
                        st.session_state.exam_id = save_exam_and_get_id(db, selected_source_ids[0], exam_title, question_ids)
                        st.session_state.exam_end_time = time.time() + exam_duration_minutes * 60
                        st.session_state.exam_state = "running"
                        db.close()
                        st.rerun()
                    else:
                        st.error("所选知识库下没有找到足够的题目来生成试卷！")
                else:
                    st.warning("请至少选择一个知识库和一种题型。")
        else:
            st.warning("没有可用于考试的知识库。")
        
        if 'db' in locals() and db.is_active:
            db.close()

elif st.session_state.exam_state == "running":
    with st.sidebar:
        st.header("⏳ 考试倒计时")
        timer_placeholder = st.empty()
    remaining_time = st.session_state.exam_end_time - time.time()
    if remaining_time > 0:
        timer_placeholder.metric("剩余时间", str(timedelta(seconds=int(remaining_time))))
    else:
        timer_placeholder.error("时间到！请尽快交卷！")
    
    st.header("考试进行中...")
    st.info(f"试卷题目数量: {len(st.session_state.exam_questions)} 道")
    with st.form("exam_form"):
        user_answers = {}
        for i, q in enumerate(st.session_state.exam_questions):
            q_id = q['id']
            st.subheader(f"第 {i+1} 题: {q['question_type']}")
            try:
                content = json.loads(q['content'])
                if q['question_type'] in ["单项选择题", "判断题"]:
                    st.write(content["question"])
                    options = content.get("options", ["正确", "错误"])
                    user_answers[q_id] = st.radio("你的答案:", options, key=f"exam_q_{q_id}", index=None, horizontal=True)
                elif q['question_type'] == "简答题":
                    st.write(content["question"])
                    user_answers[q_id] = st.text_area("你的答案:", key=f"exam_q_{q_id}")
                elif q['question_type'] == "填空题":
                    stem = content["stem"]
                    num_blanks = stem.count("___")
                    display_stem = re.sub(r'___', lambda m, c=iter(range(1, num_blanks + 1)): f"__({next(c)})__", stem)
                    st.markdown(f"{display_stem}")
                    blanks_answers = []
                    cols = st.columns(num_blanks or 1)
                    for j in range(num_blanks):
                        with cols[j]:
                            blanks_answers.append(st.text_input(f"填空 {j+1}", key=f"exam_q_{q_id}_blank_{j}"))
                    user_answers[q_id] = blanks_answers
            except Exception as e:
                st.error(f"题目(ID: {q_id})渲染失败，本题将无法计分。错误: {e}")
                continue
        
        submitted = st.form_submit_button("交卷并查看结果")
        if submitted or remaining_time <= 0:
            score = 0
            total = len(st.session_state.exam_questions)
            for q in st.session_state.exam_questions:
                try:
                    # (此处仅为示例，仅对单选题评分，可按需扩展)
                    if q['question_type'] == "单项选择题":
                        correct_answer_index = json.loads(q['answer'])["correct_option_index"]
                        options = json.loads(q['content'])["options"]
                        if user_answers.get(q['id']) == options[correct_answer_index]:
                            score += 1
                except Exception:
                    continue
            
            db = SessionLocal()
            save_exam_result(db, st.session_state.exam_id, score, total, {k: str(v) for k, v in user_answers.items() if v is not None})
            db.close()
            st.session_state.exam_result = {
                "score": score, "total": total, "questions": st.session_state.exam_questions,
                "user_answers": user_answers
            }
            st.session_state.exam_in_progress = False
            st.session_state.exam_questions = []
            st.session_state.exam_state = "finished"
            st.rerun()

    if remaining_time > 0:
        time.sleep(1)
        st.rerun()

elif st.session_state.exam_state == "finished":
    result = st.session_state.exam_result
    st.header("考后分析报告")
    st.balloons()
    tab1, tab2 = st.tabs(["📊 成绩总览", "🔍 逐题回顾"])
    with tab1:
        st.subheader("本次考试成绩")
        cols = st.columns(3)
        cols[0].metric("最终得分", f"{result['score']} / {result['total']}")
        accuracy = (result['score'] / result['total'] * 100) if result['total'] > 0 else 0
        cols[1].metric("正确率", f"{accuracy:.1f}%")
        cols[2].metric("题目总数", result['total'])
    with tab2:
        st.subheader("错题详情解析")
        has_mistake = False
        for i, q in enumerate(result['questions']):
            try:
                # (此处仅为示例，仅对单选题进行回顾，可按需扩展)
                if q['question_type'] == "单项选择题":
                    q_id = q['id']
                    content = json.loads(q['content'])
                    answer_data = json.loads(q['answer'])
                    user_ans = result['user_answers'].get(q_id)
                    correct_answer_text = content["options"][answer_data["correct_option_index"]]
                    if user_ans != correct_answer_text:
                        has_mistake = True
                        with st.expander(f"❌ 第 {i+1} 题: {content.get('question', '')[:30]}...", expanded=True):
                            st.markdown(f"**题目**: {content.get('question', '题目加载失败')}")
                            st.error(f"**你的答案**: {user_ans or '未作答'}")
                            st.success(f"**正确答案**: {correct_answer_text}")
                            if q.get('analysis'):
                                st.info(f"**解析**: {q['analysis']}")
            except Exception:
                st.warning(f"第 {i+1} 题数据存在问题，无法展示解析。")
        if not has_mistake:
            st.success("🎉 恭喜你，本次考试全部正确！")
            
    if st.button("返回考试首页", use_container_width=True):
        st.session_state.exam_state = "setup"
        st.session_state.exam_result = None
        st.rerun()