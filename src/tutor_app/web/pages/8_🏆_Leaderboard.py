# src/tutor_app/web/pages/8_🏆_Leaderboard.py
import streamlit as st
import pandas as pd
import random
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.analytics.dashboard_data import get_current_user_stats
from src.tutor_app.web.components.task_monitor import display_global_task_monitor

st.set_page_config(page_title="学习排行榜", layout="wide")
display_global_task_monitor()
st.title("🏆 学习英雄榜")

# --- 【优化1: 动态虚拟玩家】 ---

# 1. 定义虚拟玩家的基础数据
FAKE_USERS_BASE_DATA = [
    {"username": "学霸思密达", "total_practices": 1250, "total_correct": 1200},
    {"username": "卷王之王", "total_practices": 980, "total_correct": 900},
    {"username": "勤奋练习生", "total_practices": 730, "total_correct": 650},
    {"username": "小明", "total_practices": 410, "total_correct": 320},
    {"username": "潜力新星", "total_practices": 220, "total_correct": 180},
    {"username": "刚入门的萌新", "total_practices": 50, "total_correct": 35},
]

# 2. 使用 session_state 来持久化和更新虚拟玩家数据
if 'leaderboard_users' not in st.session_state:
    st.session_state.leaderboard_users = FAKE_USERS_BASE_DATA

def update_fake_users_stats():
    """
    一个辅助函数，用于模拟其他用户的学习进度。
    每次调用时，都会为虚拟玩家增加少量练习数和答对数。
    """
    for user in st.session_state.leaderboard_users:
        # 模拟练习了 0-3 道题
        practice_increase = random.randint(0, 3)
        # 模拟其中 80% 的概率答对
        correct_increase = sum([1 for _ in range(practice_increase) if random.random() < 0.85])
        
        user["total_practices"] += practice_increase
        user["total_correct"] += correct_increase

# 每次页面加载时都更新一下虚拟玩家的数据
update_fake_users_stats()


# --- 获取并整合数据 ---
db = SessionLocal()
try:
    my_stats = get_current_user_stats(db)
    # 从 session_state 获取最新的虚拟玩家数据
    all_users_data = st.session_state.leaderboard_users + [my_stats]
    
    df = pd.DataFrame(all_users_data)
    df['正确率(%)'] = (df['total_correct'] / df['total_practices'] * 100).round(2).fillna(0)
    df = df.sort_values(by="total_correct", ascending=False).reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "排名"
    df.rename(columns={
        "username": "用户名",
        "total_practices": "总练习数",
        "total_correct": "总答对数"
    }, inplace=True)

finally:
    db.close()


# --- 【优化2: 智能激励/嘲讽系统】 ---
def generate_dynamic_message(df):
    """根据用户的排名生成动态激励信息。"""
    try:
        user_row = df[df["用户名"] == "我 (You)"]
        if user_row.empty:
            return "快去做题，登上排行榜吧！"
            
        user_rank = user_row.index[0]
        user_score = user_row["总答对数"].iloc[0]
        
        if user_rank == 1:
            return "🏆 **太强了！** 您已登顶英雄榜，请继续保持，别被后面的人追上！"
        
        # 找到排在您前面的那个人
        user_above_row = df.loc[user_rank - 1]
        user_above_name = user_above_row["用户名"]
        user_above_score = user_above_row["总答对数"]
        
        score_diff = user_above_score - user_score
        
        if user_rank <= 3:
            return f"🥈 **就差一点！** 距离榜首 **{user_above_name}** 仅差 **{score_diff}** 道题，加油！"
        
        if score_diff <= 10:
             return f"👀 **紧追不舍！** 马上就要超越 **{user_above_name}** 了，再来几道题！"
        
        return f"💪 **继续努力！** 您的下一个目标是 **{user_above_name}**，还差 **{score_diff}** 道题！"
        
    except Exception:
        return "不断练习，提升排名！"

dynamic_message = generate_dynamic_message(df)
st.info(dynamic_message, icon="💡")


def highlight_user(row):
    if row["用户名"] == "我 (You)":
        return ['background-color: #3d5a80'] * len(row)
    else:
        return [''] * len(row)

# --- 页面渲染 ---
if df.empty:
    st.info("暂无排行数据，快去做题，成为第一个上榜的人吧！")
else:
    st.markdown("---")
    
    top_3 = df.head(3)
    medals = ["🥇", "🥈", "🥉"]
    cols = st.columns(3)
    
    for i in range(len(top_3)):
        row = top_3.iloc[i]
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"<h3 style='text-align: center;'>{medals[i]} {row['用户名']}</h3>", unsafe_allow_html=True)
                st.markdown("---")
                c1, c2 = st.columns(2)
                c1.metric("总答对", f"{row['总答对数']} 题")
                c2.metric("正确率", f"{row['正确率(%)']}%")

    st.markdown("---")
    
    st.subheader("完整榜单")
    
    styled_df = df.style.apply(highlight_user, axis=1)

    st.dataframe(
        styled_df,
        use_container_width=True,
        column_config={
            "正确率(%)": st.column_config.ProgressColumn(
                "正确率",
                format="%.2f%%",
                min_value=0,
                max_value=100,
            ),
        }
    )