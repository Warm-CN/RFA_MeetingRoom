# ui_pages/login.py
import streamlit as st
from auth_utils import login_user

def show_login_page():
    st.title("会议室预约系统登录")
    with st.form("login_form_main_nav"): # Unique form key
        student_id = st.text_input("学号", key="login_student_id")
        password = st.text_input("密码", type="password", key="login_password")
        submit_button = st.form_submit_button("登录")

        if submit_button:
            if login_user(student_id, password):
                st.rerun()
            else:
                st.error("学号或密码错误。")