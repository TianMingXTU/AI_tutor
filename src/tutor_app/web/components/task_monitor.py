# src/tutor_app/web/components/task_monitor.py
import streamlit as st
from celery.result import AsyncResult
from src.tutor_app.tasks.celery_app import celery_app
import time

def display_global_task_monitor():
    """
    一个可复用的Streamlit组件，用于在侧边栏显示全局的后台任务状态。
    """
    if 'active_tasks' not in st.session_state:
        st.session_state.active_tasks = {}

    active_tasks = st.session_state.active_tasks
    if not active_tasks:
        return # 如果没有活动任务，直接返回

    # 使用Expander来组织UI，避免杂乱
    with st.sidebar.expander("📊 后台任务监控", expanded=True):
        tasks_to_remove = []
        for task_id, task_info in active_tasks.items():
            task_result = AsyncResult(task_id, app=celery_app)
            
            st.markdown(f"**任务:** {task_info['name']}")

            if task_result.ready():
                # 任务已完成
                if task_result.successful():
                    st.success("状态: ✅ 已完成")
                else:
                    st.error(f"状态: ❌ 失败")
                
                # 提供一个按钮让用户可以手动清除已完成的任务
                if st.button("清除", key=f"clear_{task_id}"):
                    tasks_to_remove.append(task_id)
            else:
                # 任务正在进行中
                progress_info = task_result.info or {}
                status_text = progress_info.get('status', '正在排队...')
                st.info(f"状态: {status_text}")
            
            st.divider()

        # 从字典中移除已标记为清除的任务
        for task_id in tasks_to_remove:
            del st.session_state.active_tasks[task_id]
            st.rerun()

    # 添加一个定时刷新机制，以便自动更新状态
    time.sleep(2)
    st.rerun()