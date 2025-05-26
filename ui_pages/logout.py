# ui_pages/logout.py
import streamlit as st
from auth_utils import logout_user

def show_logout_page():
    st.title("登出系统")
    st.write("您确定要登出吗？")
    if st.button("确认登出", type="primary", key="confirm_logout_button"):
        logout_user()
        # logout_user() itself calls st.rerun(), so no need for another one here
    
    # Optional: Add a cancel button or link back
    # if st.button("取消"):
    #    st.switch_page(...) # Requires knowing the default logged-in page or using st.page_link