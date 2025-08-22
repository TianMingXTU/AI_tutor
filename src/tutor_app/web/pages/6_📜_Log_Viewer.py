# src/tutor_app/web/pages/6_📜_Log_Viewer.py
import streamlit as st
import os

LOG_FILE = "logs/app.log"

st.set_page_config(page_title="日志查看器", layout="wide")
st.title("📜 应用日志查看器")

st.info("这里显示了应用后台（包括Celery任务）的完整日志，可用于监控和调试。")

try:
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        # 读取日志文件的所有行
        log_lines = f.readlines()

    st.subheader("日志筛选与显示")
    
    # 允许用户筛选日志级别
    log_level = st.selectbox("选择日志级别:", options=["ALL", "INFO", "WARNING", "ERROR"], index=0)
    
    # 允许用户选择显示的行数
    num_lines = st.slider("显示最近的日志行数:", min_value=50, max_value=2000, value=200, step=50)

    # 过滤日志
    filtered_lines = log_lines
    if log_level != "ALL":
        filtered_lines = [line for line in log_lines if f" - {log_level} - " in line]
    
    # 获取最新的n行
    display_lines = filtered_lines[-num_lines:]

    st.subheader(f"显示最近 {len(display_lines)} 条 `{log_level}` 级别的日志")
    
    # 使用st.code展示日志内容
    log_content = "".join(display_lines)
    st.code(log_content, language='log', line_numbers=True)

    if st.button("🔄 刷新日志"):
        st.rerun()

except FileNotFoundError:
    st.error(f"日志文件 '{LOG_FILE}' 未找到。请确保后台任务已运行以生成日志文件。")
except Exception as e:
    st.error(f"读取日志时发生错误: {e}")