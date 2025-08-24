# src/tutor_app/web/pages/7_🕸️_Knowledge_Network.py
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.analytics.dashboard_data import get_knowledge_network_data
from src.tutor_app.web.components.task_monitor import display_global_task_monitor

st.set_page_config(page_title="知识网络", layout="wide")
display_global_task_monitor()
st.title("🕸️ 你的个人知识网络")
st.write("这张交互式图谱展示了你所有学习资料（知识源）与其中提炼出的核心知识点之间的联系。")

db = SessionLocal()
try:
    nodes_data, edges_data = get_knowledge_network_data(db)
finally:
    db.close()

if nodes_data:
    nodes = []
    edges = []

    for node_d in nodes_data:
        if node_d['type'] == 'source':
            # 知识源节点样式：更大，蓝色，方形
            nodes.append(Node(id=node_d['id'], label=node_d['label'], size=25, shape="box", color="#007bff"))
        else:
            # 知识点节点样式：默认大小，灰色，圆形
            nodes.append(Node(id=node_d['id'], label=node_d['label'], size=10))

    for edge_d in edges_data:
        edges.append(Edge(source=edge_d['from'], target=edge_d['to'], length=200))

    # 配置图的外观和物理引擎
    config = Config(width=1200,
                    height=800,
                    directed=True, 
                    physics=True, 
                    hierarchical=False,
                    # 美化选项
                    nodeHighlightBehavior=True,
                    highlightColor="#F7A7A6",
                    )
    
    st.info("你可以拖动节点，缩放画布，探索你的知识结构！")
    
    return_value = agraph(nodes=nodes, edges=edges, config=config)

else:
    st.warning("知识网络中还没有足够的数据。请先上传资料并生成带知识点标签的题目。")