# src/tutor_app/web/pages/5_📊_Analysis_Dashboard.py
import streamlit as st
import json
import datetime
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.db.models import KnowledgeSource
from src.tutor_app.analytics.dashboard_data import get_practice_summary, get_performance_by_source, get_mistake_notebook

st.set_page_config(page_title="学习分析", layout="wide")
st.title("📊 学习分析仪表盘 (最终版)")

db = SessionLocal()

# --- 全局筛选器 ---
with st.container(border=True):
    st.subheader("筛选器")
    
    # 知识库筛选
    all_sources = db.query(KnowledgeSource).all()
    source_options = {s.filename: s.id for s in all_sources}
    selected_sources_names = st.multiselect("选择分析范围（知识库）:", options=list(source_options.keys()), default=list(source_options.keys()))
    selected_source_ids = [source_options[name] for name in selected_sources_names]

    # 日期范围筛选
    col1, col2 = st.columns(2)
    today = datetime.date.today()
    start_date = col1.date_input("开始日期", today - datetime.timedelta(days=30))
    end_date = col2.date_input("结束日期", today)

# --- 获取经过筛选的数据 ---
summary = get_practice_summary(db, source_ids=selected_source_ids, start_date=start_date, end_date=end_date)
performance_df = get_performance_by_source(db, source_ids=selected_source_ids, start_date=start_date, end_date=end_date)
grouped_mistakes = get_mistake_notebook(db, source_ids=selected_source_ids, start_date=start_date, end_date=end_date)
db.close()

# --- 使用Tabs进行布局 ---
tab1, tab2, tab3 = st.tabs([f"📈 数据总览 ({summary['total']})", f"📚 各知识库表现", f"📒 错题本 ({sum(len(data['mistakes']) for data in grouped_mistakes.values())})"])

with tab1:
    st.header("数据总览")
    cols = st.columns(3)
    cols[0].metric("总练习次数", summary["total"])
    cols[1].metric("总正确次数", summary["correct"])
    cols[2].metric("总正确率", f"{summary['accuracy']}%")

with tab2:
    st.header("各知识库表现")
    if not performance_df.empty:
        st.dataframe(performance_df, use_container_width=True)
        st.bar_chart(performance_df.set_index('知识源')['正确率'])
    else:
        st.info("所选范围内暂无练习数据。")

with tab3:
    st.header("错题本")
    all_mistake_ids = [q.id for data in grouped_mistakes.values() for q, log in data['mistakes']]
    
    if all_mistake_ids:
        if st.button("🧠 开始本次错题集训", type="primary", use_container_width=True):
            st.session_state.practice_from_mistakes = all_mistake_ids
            st.switch_page("pages/3_✍️_Practice_Mode.py")

    if grouped_mistakes:
        for source_id, data in grouped_mistakes.items():
            with st.expander(f"**{data['name']}** ({len(data['mistakes'])} 道错题)"):
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