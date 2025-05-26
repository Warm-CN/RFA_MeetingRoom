# auth_utils.py
import streamlit as st
from werkzeug.security import generate_password_hash, check_password_hash
from database_utils import get_user_by_student_id_db

def hash_password(password):
    return generate_password_hash(password)

def verify_password(hashed_password, password):
    return check_password_hash(hashed_password, password)

def login_user(student_id, password):
    user = get_user_by_student_id_db(student_id)
    if user and verify_password(user['password_hash'], password):
        st.session_state.logged_in = True
        st.session_state.user_id = user['id']
        st.session_state.student_id = user['student_id']
        st.session_state.user_name = user['name']
        st.session_state.user_role = user['role']
        st.session_state.force_password_change = user['must_change_password_on_next_login']
        return True
    return False

def logout_user():
    keys_to_clear = [
        'logged_in', 'user_id', 'student_id', 'user_name', 
        'user_role', 'force_password_change', 'page_after_password_change'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.logged_in = False # Explicitly set
    st.rerun() # Force re-evaluation of navigation in app.py