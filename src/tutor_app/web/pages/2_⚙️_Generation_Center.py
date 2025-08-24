# src/tutor_app/web/pages/2_⚙️_Generation_Center.py
import streamlit as st
import pandas as pd
import time
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.db.models import KnowledgeSource
from src.tutor_app.tasks.generation import generate_questions_task
from src.tutor_app.core.utils import convert_to_beijing_time
from src.tutor_app.web.components.task_monitor import display_global_task_monitor

# --- 页面配置与全局组件 ---
st.set_page_config(page_title="出题中心", layout="wide")
display_global_task_monitor()

# --- 页面主体 ---
st.title("⚙️ 出题中心")
st.write("在这里，您可以根据已处理的知识库生成题目，并监控所有后台任务的状态。")

tab1, tab2 = st.tabs(["🚀 创建新任务", "📊 任务历史与监控"])

with tab1:
    with st.container(border=True):
        st.subheader("开始生成题目")
        db = SessionLocal()
        try:
            completed_sources = db.query(KnowledgeSource).filter(KnowledgeSource.status == 'completed').all()
            if completed_sources:
                source_options = {f"{s.id}: {s.filename}": s.id for s in completed_sources}
                selected_option = st.selectbox("请选择要出题的知识库:", options=list(source_options.keys()), key="gen_source_select")
                
                st.write("---")
                available_types = ["单项选择题", "判断题", "填空题", "简答题"]
                selected_types = st.multiselect("请选择要生成的题型:", options=available_types, default=["单项选择题"], key="gen_type_select")
                
                type_counts = {}
                if selected_types:
                    cols = st.columns(len(selected_types))
                    for i, q_type in enumerate(selected_types):
                        with cols[i]:
                            type_counts[q_type] = st.number_input(f"“{q_type}”数量:", min_value=1, max_value=50, value=3, key=f"gen_num_{q_type}")
                
                st.divider()
                if st.button("🚀 提交出题任务", type="primary", use_container_width=True):
                    if selected_option and type_counts:
                        source_id = source_options[selected_option]
                        
                        # 【核心改动】调用Celery任务并注册到全局监控器
                        task = generate_questions_task.delay(source_id, type_counts)
                        
                        if 'active_tasks' not in st.session_state:
                            st.session_state.active_tasks = {}
                        
                        st.session_state.active_tasks[task.id] = {
                            "name": f"为 '{selected_option}' 生成题目"
                        }

                        st.toast("题目生成任务已提交到后台！您可以在侧边栏查看进度。")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("请选择知识库并至少配置一种题型。")
            else:
                st.info("暂无可用于出题的知识库。请先在'知识库管理'页面上传并处理文件。")
        finally:
            db.close()

with tab2:
    st.subheader("知识库处理状态监控")
    auto_refresh = st.checkbox("每5秒自动刷新列表")
    db = SessionLocal()
    try:
        sources = db.query(KnowledgeSource).order_by(KnowledgeSource.created_at.desc()).all()
        if sources:
            source_data = {
                "ID": [s.id for s in sources],
                "文件名": [s.filename for s in sources],
                "状态": [s.status for s in sources],
                "创建时间": [convert_to_beijing_time(s.created_at).strftime('%Y-%m-%d %H:%M:%S') for s in sources],
            }
            df = pd.DataFrame(source_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无历史任务。")
    finally:
        db.close()
    if auto_refresh:
        time.sleep(5)
        st.rerun()