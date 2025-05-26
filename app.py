# app.py
import streamlit as st
from database_utils import init_db, create_initial_admin_if_not_exists

# Import page functions directly
from ui_pages.login import show_login_page
from ui_pages.logout import show_logout_page
from ui_pages.booking import show_booking_page
from ui_pages.manage_bookings import show_manage_bookings_page # Keep this import
from ui_pages.user_management import show_user_management_page
from ui_pages.change_password import show_change_password_page

# --- App Setup ---
st.set_page_config(page_title="会议室预约系统", layout="wide", initial_sidebar_state="expanded")
init_db()
create_initial_admin_if_not_exists("202330351561", "000000", "王祺浩")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "force_password_change" not in st.session_state: st.session_state.force_password_change = False
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "user_role" not in st.session_state: st.session_state.user_role = "user"

# --- Wrapper functions for pages with arguments ---
def show_my_bookings_wrapper():
    show_manage_bookings_page(show_all=False)

def show_all_bookings_wrapper():
    show_manage_bookings_page(show_all=True)

# --- Define Pages using st.Page ---
login_pg_def = st.Page(show_login_page, title="登录系统", icon=":material/login:")
logout_pg_def = st.Page(show_logout_page, title="登出系统", icon=":material/logout:")

booking_pg_def = st.Page(show_booking_page, title="预约会议室", icon="📅", default=True)
my_bookings_pg_def = st.Page(show_my_bookings_wrapper, title="我的预约记录", icon="📄") # Use wrapper
change_password_pg_def = st.Page(show_change_password_page, title="修改密码", icon="🔑")

user_management_pg_def = st.Page(show_user_management_page, title="用户管理 (管理员)", icon="👥")
all_bookings_pg_def = st.Page(show_all_bookings_wrapper, title="所有预约记录 (管理员)", icon="📋") # Use wrapper


# --- Navigation Logic (remains the same) ---
if not st.session_state.logged_in:
    pg = st.navigation([login_pg_def])
else:
    st.sidebar.markdown(f"### 欢迎, {st.session_state.user_name}!")
    st.sidebar.caption(f"角色: {'管理员' if st.session_state.user_role == 'admin' else '普通用户'}")
    st.sidebar.divider()

    if st.session_state.force_password_change:
        st.warning("安全提示：您需要修改您的初始/临时密码后才能访问其他功能。")
        nav_structure = {
            "账户安全": [change_password_pg_def, logout_pg_def]
        }
        pg = st.navigation(nav_structure)
    else:
        main_app_pages = [booking_pg_def]
        account_management_pages = [my_bookings_pg_def, change_password_pg_def, logout_pg_def]
        
        admin_tools_pages = []
        if st.session_state.user_role == 'admin':
            admin_tools_pages = [user_management_pg_def, all_bookings_pg_def]

        nav_config_dict = {
            "主要功能": main_app_pages,
            "我的账户": account_management_pages
        }
        if admin_tools_pages:
            nav_config_dict["管理员工具"] = admin_tools_pages
        
        pg = st.navigation(nav_config_dict)

pg.run()