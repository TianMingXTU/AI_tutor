# src/tutor_app/web/app.py
import streamlit as st
from datetime import datetime
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.analytics.dashboard_data import get_practice_summary
from src.tutor_app.db.models import Question
from src.tutor_app.crud.crud_question import get_recent_sources # <<< 导入新函数
from src.tutor_app.core.utils import convert_to_beijing_time
from src.tutor_app.core.logging import setup_logging # <<< 导入

setup_logging() # <<< 在应用开始时调用


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
    summary = get_practice_summary(db)
    total_questions = db.query(Question).count()
    recent_sources = get_recent_sources(db, 5)
except Exception as e:
    st.error(f"加载数据时出错: {e}")
    summary = {"total": 0, "accuracy": 0}
    total_questions = 0
    recent_sources = []
finally:
    db.close()

# --- 核心指标展示 ---
st.subheader("核心数据一览", divider='rainbow')
cols = st.columns(3)
with cols[0]:
    st.metric("题库题目总量", f"{total_questions} 题")
with cols[1]:
    st.metric("累计练习次数", f"{summary['total']} 次")
with cols[2]:
    st.metric("总体正确率", f"{summary['accuracy']}%")

st.divider()

col1, col2 = st.columns(2)

with col1:
    # --- 快捷操作 ---
    st.subheader("快捷入口")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✍️ 开始新的练习", use_container_width=True, type="primary"):
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