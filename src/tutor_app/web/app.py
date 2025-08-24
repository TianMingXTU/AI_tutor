# src/tutor_app/web/app.py
import streamlit as st
from datetime import datetime, date
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.analytics.dashboard_data import get_practice_summary
from src.tutor_app.db.models import Question
# 【优化1】导入新的CRUD函数
from src.tutor_app.crud.crud_question import get_recent_sources, count_review_questions_today
from src.tutor_app.core.utils import convert_to_beijing_time
from src.tutor_app.core.logging import setup_logging

setup_logging()

st.set_page_config(
    page_title="AI 学习与测评平台",
    page_icon="🚀",
    layout="wide"
)

# 初始化 Session State
if "today_date" not in st.session_state:
    st.session_state.today_date = convert_to_beijing_time(datetime.utcnow()).strftime("%Y年%m月%d日")

st.title("🚀 个人AI学习与测评平台")
st.caption(f"今天是 {st.session_state.today_date}，又是充满希望的一天！") 

# --- 获取核心数据 ---
db = SessionLocal()
try:
    # 宏观数据
    overall_summary = get_practice_summary(db)
    total_questions = db.query(Question).count()
    recent_sources = get_recent_sources(db, 5)
    
    # 【优化2】获取今日待复习和今日学习数据
    review_count_today = count_review_questions_today(db)
    today_summary = get_practice_summary(db, start_date=date.today(), end_date=date.today())

except Exception as e:
    st.error(f"加载数据时出错: {e}")
    overall_summary = {"total": 0, "accuracy": 0}
    total_questions = 0
    recent_sources = []
    review_count_today = 0
    today_summary = {"total": 0, "correct": 0, "accuracy": 0}
finally:
    db.close()

# --- 【优化3: “行动号召”模块】 ---
st.markdown("---")
if review_count_today > 0:
    with st.container(border=True):
        st.subheader("🔔 智能复习提醒")
        st.info(f"您今天有 **{review_count_today}** 道题目需要复习，这是巩固记忆的最佳时机！")
        if st.button("🧠 立即开始智能复习", type="primary", use_container_width=True):
            # 设置一个session state标志，以便刷题页面加载时直接进入复习模式
            st.session_state.start_smart_review = True
            st.switch_page("pages/3_✍️_Practice_Mode.py")
else:
    st.success("🎉 恭喜！今天没有需要复习的旧题目，非常适合学习新知识！")
st.markdown("---")


# --- 今日学习与核心指标 ---
col1, col2 = st.columns(2)

with col1:
    # --- 【优化4: “今日学习小结”模块】 ---
    st.subheader("今日学习小结")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("今日练习题数", f"{today_summary['total']} 题")
        c2.metric("今日答对题数", f"{today_summary['correct']} 题")
        c3.metric("今日正确率", f"{today_summary['accuracy']}%")

with col2:
    st.subheader("核心数据总览")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("题库题目总量", f"{total_questions} 题")
        c2.metric("累计练习次数", f"{overall_summary['total']} 次")
        c3.metric("总体正确率", f"{overall_summary['accuracy']}%")


st.divider()

# --- 快捷入口与近期上传 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("快捷入口")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✍️ 开始新的练习", use_container_width=True):
                st.switch_page("pages/3_✍️_Practice_Mode.py")
            if st.button("📝 进行模拟考试", use_container_width=True):
                st.switch_page("pages/4_📝_Mock_Exam.py")
        with c2:
            if st.button("📚 上传学习资料", use_container_width=True):
                st.switch_page("pages/1_📚_Knowledge_Base.py")
            if st.button("📊 查看学习分析", use_container_width=True):
                st.switch_page("pages/5_📊_Analysis_Dashboard.py")
            
with col2:
    st.subheader("近期上传")
    with st.container(border=True):
        if recent_sources:
            for source in recent_sources:
                beijing_time = convert_to_beijing_time(source.created_at)
                st.markdown(f"- **{source.filename}** (状态: `{source.status}`) - *{beijing_time.strftime('%Y-%m-%d')}*")
        else:
            st.info("暂无上传记录。")