# src/tutor_app/web/pages/2_⚙️_Generation_Center.py
import streamlit as st
import pandas as pd
import time
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.db.models import KnowledgeSource
from src.tutor_app.tasks.generation import generate_questions_task
from src.tutor_app.core.utils import convert_to_beijing_time

st.set_page_config(page_title="出题中心", layout="wide")
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
                        
                        with st.status("出题任务已提交，正在后台生成...", expanded=True) as status:
                            # --- 【核心修复】将包含多种题型和数量的字典直接传递给Celery任务 ---
                            # 现在的调用方式是 (source_id, type_counts)，与后端定义完全匹配
                            task = generate_questions_task.delay(source_id, type_counts)
                            
                            status.update(label=f"任务已派发 (ID: {task.id})，等待AI引擎响应...")
                            total_questions = sum(type_counts.values())

                            while not task.ready():
                                progress_info = task.info or {}
                                current = progress_info.get('current', 0)
                                status_text = progress_info.get('status', 'AI正在创作中...')
                                status.update(label=f"{status_text} ({current}/{total_questions})")
                                time.sleep(2)
                            
                            if task.state == 'SUCCESS':
                                result = task.result
                                status.update(label=f"任务完成！成功生成 {result.get('generated', 0)} 道题。", state="complete", expanded=False)
                                st.balloons()
                            else:
                                status.update(label="任务失败！详情请查看日志。", state="error", expanded=True)
                                st.error(f"任务失败信息: {task.info}")
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