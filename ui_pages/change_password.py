# ui_pages/change_password.py
import streamlit as st
from database_utils import get_user_by_id_db, update_user_password_db
from auth_utils import verify_password, hash_password

def show_change_password_page():
    st.subheader("修改密码")
    user_id = st.session_state.get('user_id')

    if not user_id:
        st.error("无法获取用户信息，请重新登录。")
        return

    with st.form("change_password_form_nav"):
        old_pass = st.text_input("旧密码", type="password", key="cp_old_pass_nav")
        new_pass = st.text_input("新密码", type="password", key="cp_new_pass_nav")
        confirm_new_pass = st.text_input("确认新密码", type="password", key="cp_confirm_pass_nav")
        submit_btn = st.form_submit_button("确认修改")

        if submit_btn:
            if not old_pass or not new_pass or not confirm_new_pass:
                st.warning("所有密码字段均为必填项。")
                return

            user_data = get_user_by_id_db(user_id) # Fetches password_hash
            if user_data and verify_password(user_data['password_hash'], old_pass):
                if new_pass == confirm_new_pass:
                    if len(new_pass) < 6: # Basic password policy example
                        st.error("新密码长度至少为6位。")
                    else:
                        new_hashed_pass = hash_password(new_pass)
                        if update_user_password_db(user_id, new_hashed_pass):
                            st.session_state.force_password_change = False
                            st.success("密码修改成功！")
                            # Optional: redirect or clear form
                            # st.rerun() # Rerun to reflect change and potentially update navigation
                        else:
                            st.error("更新密码时发生数据库错误。")
                else:
                    st.error("新密码与确认密码不匹配。")
            else:
                st.error("旧密码不正确。")