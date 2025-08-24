# src/tutor_app/web/pages/5_📊_Analysis_Dashboard.py
import streamlit as st
import json
import datetime
import pandas as pd
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.db.models import KnowledgeSource
# 【优化1】导入所有需要的函数
from src.tutor_app.analytics.dashboard_data import (
    get_practice_summary, 
    get_performance_by_source, 
    get_mistake_notebook,
    get_srs_review_forecast,
    get_hardest_questions
)
from src.tutor_app.web.components.task_monitor import display_global_task_monitor

st.set_page_config(page_title="学习分析", layout="wide")
display_global_task_monitor()
st.title("📊 学习分析仪表盘")

db = SessionLocal()

# --- 全局筛选器 (保持不变) ---
with st.container(border=True):
    st.subheader("筛选器")
    
    all_sources = db.query(KnowledgeSource).all()
    source_options = {s.filename: s.id for s in all_sources}
    selected_sources_names = st.multiselect("选择分析范围（知识库）:", options=list(source_options.keys()), default=list(source_options.keys()))
    selected_source_ids = [source_options[name] for name in selected_sources_names]

    col1, col2 = st.columns(2)
    today = datetime.date.today()
    start_date = col1.date_input("开始日期", today - datetime.timedelta(days=30))
    end_date = col2.date_input("结束日期", today)

# --- 【优化2】获取所有分析所需的数据 ---
summary = get_practice_summary(db, source_ids=selected_source_ids, start_date=start_date, end_date=end_date)
performance_df = get_performance_by_source(db, source_ids=selected_source_ids, start_date=start_date, end_date=end_date)
grouped_mistakes = get_mistake_notebook(db, source_ids=selected_source_ids, start_date=start_date, end_date=end_date)
# 调用新函数获取记忆健康度数据
review_forecast_df = get_srs_review_forecast(db)
hardest_questions = get_hardest_questions(db)
db.close()

# --- 【优化3】增加新的Tab并重新排序 ---
tab1, tab2, tab3, tab4 = st.tabs([
    f"📈 数据总览", 
    f"🧠 记忆健康度", # 新增的Tab
    f"📚 各知识库表现", 
    f"📒 错题本 ({sum(len(data['mistakes']) for data in grouped_mistakes.values())})"
])

with tab1:
    st.header("数据总览")
    st.info(f"以下数据统计范围为 **{start_date}** 至 **{end_date}**")
    cols = st.columns(3)
    cols[0].metric("总练习次数", summary["total"])
    cols[1].metric("总正确次数", summary["correct"])
    cols[2].metric("总正确率", f"{summary['accuracy']}%")

# --- 【优化4】渲染“记忆健康度”新页面的内容 ---
with tab2:
    st.header("记忆健康度分析")
    st.info("此页面基于您的“智能复习”历史，洞察您的记忆规律。")

    st.subheader("🗓️ 未来30天复习压力图")
    if not review_forecast_df.empty:
        st.bar_chart(review_forecast_df)
    else:
        st.write("未来30天内没有待复习的题目。")
    
    st.divider()

    st.subheader("🧠 十大“顽固”知识点")
    st.warning("这些是您最容易忘记或感到困难的题目（基于简易度因子 `ease_factor` 排序），请重点关注。")
    if hardest_questions:
        for i, (question, stats) in enumerate(hardest_questions):
            with st.expander(f"**Top {i+1}:** {json.loads(question.content)['question'][:50]}..."):
                st.error(f"**题目**:{json.loads(question.content)['question']}")
                st.info(f"**答案**:{json.loads(question.answer)}")
                st.divider()
                stat_cols = st.columns(3)
                stat_cols[0].metric("简易度因子", f"{stats.ease_factor:.2f}", help="值越低表示越难，最低为1.3")
                stat_cols[1].metric("正确复习次数", stats.repetitions)
                stat_cols[2].metric("下次复习间隔", f"{stats.interval} 天")
    else:
        st.write("暂无记忆数据，请先在“智能复习”模式下进行练习。")


with tab3:
    st.header("各知识库表现")
    if not performance_df.empty:
        st.dataframe(performance_df, use_container_width=True)
        st.bar_chart(performance_df.set_index('知识源')['正确率'])
    else:
        st.info("所选范围内暂无练习数据。")

with tab4:
    st.header("错题本")
    all_mistake_ids = [q.id for data in grouped_mistakes.values() for q, log in data['mistakes']]
    
    if all_mistake_ids:
        if st.button("🧠 开始本次错题集训", type="primary", use_container_width=True):
            st.session_state.practice_from_mistakes = all_mistake_ids
            st.switch_page("pages/3_✍️_Practice_Mode.py")

    if grouped_mistakes:
        for source_id, data in grouped_mistakes.items():
            with st.expander(f"**{data['name']}** ({len(data['mistakes'])} 道错题)"):
                # ... (错题本内部逻辑保持不变)
                for i, (question, log) in enumerate(data['mistakes']):
                    st.markdown(f"**错题 {i+1} (ID: {question.id})**: {json.loads(question.content)['question']}")
                    st.error(f"**你的错误答案**: {log.user_answer}")
                    correct_answer_text = "解析失败"
                    try:
                        content = json.loads(question.content)
                        answer_data = json.loads(question.answer)
                        if question.question_type == "单项选择题": correct_answer_text = content["options"][answer_data["correct_option_index"]]
                        elif question.question_type == "判断题": correct_answer_text = "正确" if answer_data["correct_answer"] else "错误"
                        elif question.question_type == "填空题": correct_answer_text = ", ".join(answer_data["blanks"])
                        elif question.question_type == "简答题": correct_answer_text = answer_data["text"]
                    except Exception: pass
                    st.success(f"**正确答案**: {correct_answer_text}")
                    if question.analysis:
                        st.info(f"**解析**: {question.analysis}")
                    st.divider()
    else:
        st.success("太棒了！所选范围内没有发现错题。")