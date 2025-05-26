# ui_pages/user_management.py
import streamlit as st
import pandas as pd
from database_utils import (
    get_all_users_db, 
    add_user_db, 
    delete_user_db, 
    update_user_role_db,
    reset_user_password_db,
    get_user_by_student_id_db
)
from auth_utils import hash_password

def show_user_management_page(): # Admin only
    st.subheader("用户管理")

    users = get_all_users_db()
    if users:
        df_users = pd.DataFrame(users)
        df_users_display = df_users.rename(columns={
            'id':'ID', 'student_id':'学号', 'name':'姓名', 'role':'角色', 
            'must_change_password_on_next_login': '下次登录需改密'
        })
        st.dataframe(df_users_display[['ID', '学号', '姓名', '角色', '下次登录需改密']])
    else:
        st.info("系统中没有用户。")

    st.markdown("---")
    with st.expander("添加新用户"):
        with st.form("admin_add_user_form_nav"):
            new_sid = st.text_input("学号 (登录账号)", key="admin_add_sid_nav")
            new_name_val = st.text_input("姓名", key="admin_add_name_nav")
            new_pass = st.text_input("初始密码", type="password", key="admin_add_pass_nav")
            new_role_val = st.selectbox("角色", options=["user", "admin"], index=0, key="admin_add_role_nav")
            add_user_submit_btn = st.form_submit_button("添加用户")

            if add_user_submit_btn:
                if not new_sid or not new_name_val or not new_pass:
                    st.warning("请填写所有必填项（学号、姓名、密码）。")
                else:
                    existing = get_user_by_student_id_db(new_sid)
                    if existing:
                        st.error(f"学号 '{new_sid}' 已被注册。")
                    else:
                        hashed_pass = hash_password(new_pass)
                        if add_user_db(new_sid, new_name_val, hashed_pass, new_role_val):
                            st.success(f"用户 '{new_name_val}' ({new_sid}) 添加成功。用户下次登录需修改密码。")
                            st.rerun()
                        # Error is handled in add_user_db

    if users:
        st.markdown("---")
        st.subheader("管理现有用户")
        
        user_options_dict_admin = {u['id']: f"{u['name']} ({u['student_id']})" for u in users}
        options_list_admin = [""] + list(user_options_dict_admin.keys())

        selected_user_id_admin = st.selectbox(
            "选择用户进行操作",
            options=options_list_admin,
            format_func=lambda x: user_options_dict_admin.get(x, "请选择用户..."),
            key="admin_select_user_to_manage_nav"
        )

        if selected_user_id_admin:
            selected_user = next((u for u in users if u['id'] == selected_user_id_admin), None)

            if selected_user:
                st.write(f"正在管理用户: **{selected_user['name']} ({selected_user['student_id']})**")

                # Delete User
                if st.button(f"删除用户", key=f"admin_del_user_{selected_user_id_admin}", type="primary"):
                    if selected_user_id_admin == st.session_state.get('user_id'):
                        st.error("不能删除当前登录的管理员账户。")
                    else:
                        if delete_user_db(selected_user_id_admin):
                            st.success(f"用户 {selected_user['name']} 已删除。")
                            st.rerun()
                
                # Edit Role
                st.markdown("---")
                current_role_idx = 0 if selected_user['role'] == 'user' else 1
                new_role_for_edit = st.selectbox(
                    "修改角色为", 
                    options=["user", "admin"], 
                    index=current_role_idx, 
                    key=f"admin_edit_role_{selected_user_id_admin}"
                )
                if st.button(f"确认修改角色", key=f"admin_submit_role_edit_{selected_user_id_admin}"):
                    if selected_user_id_admin == st.session_state.get('user_id') and new_role_for_edit == 'user':
                         st.error("管理员不能将自己降级为普通用户。")
                    elif selected_user['role'] == new_role_for_edit:
                        st.info("角色未发生改变。")
                    else:
                        if update_user_role_db(selected_user_id_admin, new_role_for_edit):
                            st.success(f"用户角色已更新为 {new_role_for_edit}。")
                            st.rerun()

                # Reset Password
                st.markdown("---")
                st.write(f"**重置用户 {selected_user['name']} 的密码：**") # Section title
                
                reset_button_key = f"admin_reset_pass_btn_{selected_user_id_admin}"
                if st.button(f"为此用户重置密码", key=reset_button_key):
                    temp_pass_value = selected_user['student_id'] + "ResetXYZ!" # Make it slightly different
                    hashed_temp = hash_password(temp_pass_value)
                    if reset_user_password_db(selected_user_id_admin, hashed_temp):
                        # Store in session state, specific to this user being managed
                        st.session_state[f"temp_pass_for_{selected_user_id_admin}"] = temp_pass_value
                        st.success(f"密码已重置。临时密码已生成（见下方）。用户下次登录需修改密码。")
                        st.rerun() # Rerun to display the temp password below
                    else:
                        st.error("数据库重置密码时出错。")
                
                # Display temporary password if it's in session state for this user
                temp_pass_session_key = f"temp_pass_for_{selected_user_id_admin}"
                if temp_pass_session_key in st.session_state:
                    st.info(f"临时密码: **{st.session_state[temp_pass_session_key]}** (请安全告知用户)")
                    if st.button("清除此临时密码显示", key=f"clear_temp_pass_{selected_user_id_admin}"):
                        del st.session_state[temp_pass_session_key]
                        st.rerun()