# src/tutor_app/web/pages/1_📚_Knowledge_Base.py
import streamlit as st
import os
import time
from sqlalchemy.orm import Session
from src.tutor_app.db.session import SessionLocal
from src.tutor_app.db.models import KnowledgeSource
from src.tutor_app.tasks.processing import process_file_task
from src.tutor_app.core.utils import convert_to_beijing_time
from src.tutor_app.crud.crud_question import count_questions_by_source, delete_source_and_related_data

UPLOAD_DIRECTORY = "data/uploaded_files"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

st.set_page_config(page_title="知识库管理", layout="wide")
st.title("📚 知识库管理")

col1, col2 = st.columns([1, 2])

with col1:
    with st.container(border=True):
        st.subheader("上传新资料")
        uploaded_file = st.file_uploader("上传您的PDF学习资料", type="pdf", label_visibility="collapsed")

        if uploaded_file is not None:
            filepath = os.path.join(UPLOAD_DIRECTORY, uploaded_file.name)
            with open(filepath, "wb") as f:
                f.write(uploaded_file.getbuffer())

            if st.button("提交到后台处理", type="primary", use_container_width=True):
                db: Session = SessionLocal()
                try:
                    existing_source = db.query(KnowledgeSource).filter_by(filename=uploaded_file.name).first()
                    if existing_source:
                        st.warning("同名文件已存在，请重命名后上传或删除旧文件。")
                    else:
                        new_source = KnowledgeSource(filename=uploaded_file.name, status="pending")
                        db.add(new_source)
                        db.commit()
                        db.refresh(new_source)
                        source_id = new_source.id
                        
                        # 【核心优化】使用st.status来追踪任务进度
                        with st.status(f"文件处理任务已提交 (ID: {source_id})...", expanded=True) as status:
                            task = process_file_task.delay(source_id=source_id)
                            st.write(f"正在等待Celery Worker接收任务...")
                            
                            while not task.ready():
                                # 轮询任务状态
                                progress_info = task.info or {}
                                current = progress_info.get('current', 0)
                                total = progress_info.get('total', 1)
                                status_text = progress_info.get('status', '正在处理...')
                                
                                # 更新进度条
                                progress_value = current / total if total > 0 else 0
                                status.update(label=f"处理中: {status_text} ({current}/{total})")
                                time.sleep(1)
                            
                            if task.state == 'SUCCESS':
                                status.update(label="文件处理完成！", state="complete", expanded=False)
                                st.success("文件处理成功！刷新列表查看最新状态。")
                            else:
                                status.update(label="任务失败！", state="error", expanded=True)
                                st.error(f"任务处理失败: {task.info}")

                except Exception as e:
                    st.error(f"提交任务时发生错误: {e}")
                finally:
                    db.close()

with col2:
    st.subheader("已有知识库")
    if st.button("🔄 刷新列表"):
        st.rerun()

    db = SessionLocal()
    try:
        sources = db.query(KnowledgeSource).order_by(KnowledgeSource.created_at.desc()).all()
        if not sources:
            st.info("暂无已入库的知识源。")
        else:
            for source in sources:
                with st.expander(f"**{source.filename}** (ID: {source.id})"):
                    # 获取额外信息
                    num_questions = count_questions_by_source(db, source.id)
                    beijing_time = convert_to_beijing_time(source.created_at)

                    # 使用列展示详细信息
                    c1, c2, c3 = st.columns(3)
                    c1.metric("状态", source.status)
                    c2.metric("已生成题目数", num_questions)
                    c3.caption(f"入库时间:\n{beijing_time.strftime('%Y-%m-%d %H:%M')}")
                    
                    st.divider()
                    
                    # 定义删除的回调函数
                    def delete_action(s_id):
                        try:
                            db_delete = SessionLocal()
                            delete_source_and_related_data(db_delete, s_id)
                            db_delete.close()
                            st.toast(f"已删除知识源 {s_id} 及其关联数据！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"删除时出错: {e}")

                    # 增加二次确认
                    if f"confirm_delete_{source.id}" not in st.session_state:
                        st.session_state[f"confirm_delete_{source.id}"] = False

                    def toggle_confirm_delete(s_id):
                        st.session_state[f"confirm_delete_{s_id}"] = not st.session_state[f"confirm_delete_{s_id}"]

                    if st.session_state[f"confirm_delete_{source.id}"]:
                        st.warning(f"⚠️ 您确定要删除 **{source.filename}** 吗？\n\n这将一并删除所有从此文件生成的题目和相关的练习记录，此操作不可逆！")
                        c_del_1, c_del_2 = st.columns(2)
                        with c_del_1:
                            st.button("确认删除", key=f"confirm_del_btn_{source.id}", use_container_width=True, type="primary", on_click=delete_action, args=(source.id,))
                        with c_del_2:
                            st.button("取消", key=f"cancel_del_btn_{source.id}", use_container_width=True, on_click=toggle_confirm_delete, args=(source.id,))
                    else:
                        st.button("删除此知识源", key=f"del_btn_{source.id}", use_container_width=True, on_click=toggle_confirm_delete, args=(source.id,))
    finally:
        db.close()