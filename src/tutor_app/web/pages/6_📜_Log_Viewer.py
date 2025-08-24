# src/tutor_app/web/pages/6_📜_Log_Viewer.py
import streamlit as st
import os
import re
import pandas as pd
import time

LOG_FILE = "logs/app.log"

st.set_page_config(page_title="日志查看器", layout="wide")
st.title("📜 智能日志查看器")
st.info("这里以更友好的方式显示应用后台日志。您可以搜索、筛选并查看高亮显示的重要信息。")

# --- 【优化核心1: 日志解析函数】 ---
# 使用正则表达式来解析每一行日志
LOG_REGEX = re.compile(r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (?P<module>.*?) - (?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL) - (?P<message>[\s\S]*)')

def parse_log_line(line):
    """将单行日志字符串解析为结构化的字典。"""
    match = LOG_REGEX.match(line)
    if match:
        return match.groupdict()
    return None

def load_logs():
    """加载并解析整个日志文件。"""
    if not os.path.exists(LOG_FILE):
        return []
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    parsed_logs = [parse_log_line(line) for line in lines]
    # 过滤掉无法解析的行，并倒序排列（最新的在最前面）
    return [log for log in parsed_logs if log is not None][::-1]

# --- 页面主逻辑 ---
logs = load_logs()

if not logs:
    st.warning(f"日志文件 '{LOG_FILE}' 未找到或内容为空。请确保后台任务已运行以生成日志文件。")
else:
    # --- 【优化核心2: 筛选与搜索控件】 ---
    with st.container(border=True):
        st.subheader("筛选与搜索")
        
        cols = st.columns([1, 2, 1])
        with cols[0]:
            # 按级别筛选
            log_level = st.selectbox(
                "日志级别:", 
                options=["ALL", "INFO", "WARNING", "ERROR"], 
                index=0,
                label_visibility="collapsed"
            )
        with cols[1]:
            # 关键词搜索
            search_term = st.text_input(
                "搜索关键词:", 
                placeholder="输入任务ID, 文件名, 错误信息等...",
                label_visibility="collapsed"
            )
        with cols[2]:
            num_lines = st.number_input(
            "显示条数",
            min_value=10, 
            max_value=len(logs), 
            value=min(100, len(logs)), # <-- 使用min()函数确保默认值不超过最大值
            step=20,
            label_visibility="collapsed"
        )

    # --- 应用筛选逻辑 ---
    filtered_logs = logs
    
    if log_level != "ALL":
        filtered_logs = [log for log in filtered_logs if log['level'] == log_level]
    
    if search_term:
        filtered_logs = [log for log in filtered_logs if search_term.lower() in log['message'].lower()]

    # 应用显示条数限制
    display_logs = filtered_logs[:num_lines]
    
    st.markdown("---")
    st.subheader(f"共找到 {len(filtered_logs)} 条匹配日志，显示最近的 {len(display_logs)} 条")
    
    # --- 【优化核心3: 结构化与颜色高亮展示】 ---
    for log in display_logs:
        level = log['level']
        
        # 根据日志级别选择不同的颜色和图标
        if level == "ERROR":
            expander_title = f"❌ **[ERROR]** {log['timestamp']} - {log['module']}"
            with st.expander(expander_title):
                st.error(log['message'], icon="🚨")
        elif level == "WARNING":
            expander_title = f"⚠️ **[WARNING]** {log['timestamp']} - {log['module']}"
            with st.expander(expander_title):
                st.warning(log['message'], icon="⚠️")
        else: # INFO and others
            expander_title = f"ℹ️ [INFO] {log['timestamp']} - {log['module']}"
            with st.expander(expander_title):
                st.info(log['message'], icon="ℹ️")
    
    st.markdown("---")
    # --- 【优化核心4: 自动刷新】 ---
    c1, c2 = st.columns([1, 3])
    with c1:
        auto_refresh = st.checkbox("每5秒自动刷新")
    if auto_refresh:
        with c2:
            st.write("🔄 页面将在5秒后自动刷新...")
        time.sleep(5)
        st.rerun()