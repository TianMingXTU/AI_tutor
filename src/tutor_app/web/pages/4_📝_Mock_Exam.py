# src/tutor_app/web/pages/4_📝_Mock_Exam.py
import streamlit as st
import json
import time
import re
import pandas as pd
from datetime import timedelta
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.db.models import KnowledgeSource
# 【优化1】导入所有需要的函数和模型
from src.tutor_app.crud.crud_question import (
    get_question_batch_with_type_selection, 
    save_exam_and_get_id, 
    save_exam_result,
    create_log_for_grading,
    get_grading_results
)
from src.tutor_app.tasks.grading import grade_short_answer_task
from src.tutor_app.web.components.task_monitor import display_global_task_monitor

st.set_page_config(page_title="模拟考试", layout="wide")
display_global_task_monitor()
st.title("📝 模拟考试模式")

# ... (analyze_exam_by_tag, question_to_dict, Session State 初始化保持不变)
def analyze_exam_by_tag(questions, user_answers):
    tag_stats = {}
    for q in questions:
        q_id = q['id']
        tag = q.get('knowledge_tag')
        if not tag: continue
        if tag not in tag_stats: tag_stats[tag] = {"correct": 0, "total": 0}
        tag_stats[tag]["total"] += 1
        user_ans = user_answers.get(q_id)
        is_correct = False
        try:
            content = json.loads(q['content'])
            answer_data = json.loads(q['answer'])
            if q['question_type'] == "单项选择题":
                correct_answer_text = content["options"][answer_data["correct_option_index"]]
                if user_ans == correct_answer_text: is_correct = True
            elif q['question_type'] == "判断题":
                correct_answer_text = "正确" if answer_data["correct_answer"] else "错误"
                if user_ans == correct_answer_text: is_correct = True
        except Exception: pass
        if is_correct: tag_stats[tag]["correct"] += 1
    if not tag_stats: return pd.DataFrame()
    df_data = []
    for tag, stats in tag_stats.items():
        accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
        df_data.append({"知识点": tag, "题目总数": stats['total'], "答对题数": stats['correct'], "正确率(%)": round(accuracy, 2)})
    return pd.DataFrame(df_data)

def question_to_dict(q):
    return {"id": q.id, "question_type": q.question_type, "content": q.content, "answer": q.answer, "analysis": q.analysis, "knowledge_tag": q.knowledge_tag}

if 'exam_state' not in st.session_state: st.session_state.exam_state = "setup"
if 'exam_questions' not in st.session_state: st.session_state.exam_questions = []
if 'exam_id' not in st.session_state: st.session_state.exam_id = None
if 'exam_result' not in st.session_state: st.session_state.exam_result = None
if 'exam_end_time' not in st.session_state: st.session_state.exam_end_time = None


if st.session_state.exam_state == "setup":
    # ... (设置界面代码保持不变)
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
            selected_types = st.multiselect("请选择试卷包含的题型:", options=available_types, default=["单项选择题", "判断题", "简答题"])
            type_counts = {}
            if selected_types:
                cols = st.columns(len(selected_types))
                for i, q_type in enumerate(selected_types):
                    with cols[i]:
                        type_counts[q_type] = st.number_input(f"“{q_type}”数量:", min_value=1, max_value=50, value=2, key=f"exam_num_{q_type}")
            
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
    # ... (考试进行中界面代码保持不变)
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
            db = SessionLocal()
            try:
                # --- 【优化2: 交卷时触发AI评分】 ---
                score = 0
                total = len(st.session_state.exam_questions)
                grading_log_ids_map = {}

                for q in st.session_state.exam_questions:
                    q_id = q['id']
                    user_ans = user_answers.get(q_id)
                    
                    if q['question_type'] == "简答题" and user_ans and user_ans.strip():
                        # 1. 为简答题创建评分日志
                        log_id = create_log_for_grading(db, q_id, user_ans)
                        grading_log_ids_map[q_id] = log_id
                        # 2. 派发异步评分任务
                        grade_short_answer_task.delay(log_id)
                    else:
                        # 3. 为客观题直接评分
                        is_correct = False
                        try:
                            content = json.loads(q['content'])
                            answer_data = json.loads(q['answer'])
                            if q['question_type'] == "单项选择题":
                                correct_answer_text = content["options"][answer_data["correct_option_index"]]
                                if user_ans == correct_answer_text: is_correct = True
                            elif q['question_type'] == "判断题":
                                correct_answer_text = "正确" if answer_data["correct_answer"] else "错误"
                                if user_ans == correct_answer_text: is_correct = True
                            if is_correct:
                                score += 1
                        except Exception:
                            continue
                
                # 4. 保存考试结果，包括简答题的log_id映射
                save_exam_result(
                    db, st.session_state.exam_id, score, total, 
                    {k: str(v) for k, v in user_answers.items() if v is not None},
                    grading_log_ids_map
                )
                
                # 5. 更新 session_state
                st.session_state.exam_result = {
                    "score": score, "total": total, "questions": st.session_state.exam_questions,
                    "user_answers": user_answers,
                    "grading_log_ids": grading_log_ids_map
                }
                st.session_state.exam_state = "finished"
                st.rerun()
            finally:
                db.close()

    if remaining_time > 0:
        time.sleep(1)
        st.rerun()

elif st.session_state.exam_state == "finished":
    result = st.session_state.exam_result
    st.header("考后分析报告")
    st.balloons()
    
    tag_analysis_df = analyze_exam_by_tag(result['questions'], result['user_answers'])
    
    # --- 【优化3: 在报告中查询并展示AI评分结果】 ---
    grading_log_ids = result.get("grading_log_ids", {})
    db = SessionLocal()
    try:
        grading_results = get_grading_results(db, list(grading_log_ids.values()))
    finally:
        db.close()

    tab1, tab2, tab3 = st.tabs(["📊 成绩总览", "🏷️ 知识点诊断", "🔍 逐题回顾"])
    
    with tab1:
        # ... (成绩总览代码不变)
        st.subheader("本次考试成绩")
        cols = st.columns(3)
        cols[0].metric("最终得分", f"{result['score']} / {result['total']}")
        accuracy = (result['score'] / result['total'] * 100) if result['total'] > 0 else 0
        cols[1].metric("正确率", f"{accuracy:.1f}%")
        cols[2].metric("题目总数", result['total'])
    
    with tab2:
        # ... (知识点诊断代码不变)
        st.subheader("本次考试知识点诊断")
        if not tag_analysis_df.empty:
            st.info("这份诊断报告分析了您在本次考试中，各个知识点的表现。请重点关注正确率较低的环节。")
            sorted_df = tag_analysis_df.sort_values(by='正确率(%)', ascending=True)
            st.dataframe(sorted_df, use_container_width=True)
            st.bar_chart(sorted_df.set_index('知识点')['正确率(%)'])
        else:
            st.warning("本次考试的题目缺少知识点标签，无法生成诊断报告。")

    with tab3:
        st.subheader("题目详情回顾")
        for i, q in enumerate(result['questions']):
            q_id = q['id']
            with st.expander(f"第 {i+1} 题 ({q['question_type']}): {json.loads(q['content']).get('question', '')[:30]}..."):
                st.markdown(f"**题目**: {json.loads(q['content']).get('question', '题目加载失败')}")
                user_ans = result['user_answers'].get(q_id)
                st.error(f"**你的答案**: {user_ans or '未作答'}")

                if q['question_type'] == "简答题":
                    log_id = grading_log_ids.get(q_id)
                    log_entry = grading_results.get(log_id)
                    if log_entry and log_entry.ai_score:
                        score_map = {"正确": "success", "部分正确": "warning", "错误": "error"}
                        score_type = score_map.get(log_entry.ai_score, "info")
                        getattr(st, score_type)(f"**AI 评价**: {log_entry.ai_score}")
                        st.info(f"**AI 评语**: {log_entry.ai_feedback}")
                    else:
                        st.info("🤖 AI 助教正在批阅您的答案，请稍后刷新...")
                else: # 客观题
                    try:
                        content = json.loads(q['content'])
                        answer_data = json.loads(q['answer'])
                        correct_answer_text = ""
                        if q['question_type'] == "单项选择题":
                            correct_answer_text = content["options"][answer_data["correct_option_index"]]
                        elif q['question_type'] == "判断题":
                            correct_answer_text = "正确" if answer_data["correct_answer"] else "错误"
                        st.success(f"**正确答案**: {correct_answer_text}")
                    except:
                        st.warning("答案解析失败。")

                if q.get('analysis'):
                    with st.expander("💡 查看原题解析"):
                        st.info(f"**原题解析**: {q['analysis']}")
            
    if st.button("返回考试首页", use_container_width=True):
        st.session_state.exam_state = "setup"
        st.session_state.exam_result = None
        st.rerun()