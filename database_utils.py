# database_utils.py
import streamlit as st
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash # For initial admin only

# --- Connection (Cached Resource) ---
@st.cache_resource(ttl=3600) # Cache the connection for 1 hour
def get_db_connection():
    # st.write("DEBUG: Attempting to create/retrieve DB connection...") # For debugging cache
    try:
        conn = mysql.connector.connect(
            host=st.secrets["database"]["host"],
            user=st.secrets["database"]["user"],
            password=st.secrets["database"]["password"],
            database=st.secrets["database"]["database_name"]
        )
        # st.write("DEBUG: DB Connection successful.") # For debugging
        return conn
    except Error as e:
        st.error(f"数据库连接错误: {e}")
        return None
    except Exception as e: # Catch potential KeyError if secrets are not set
        st.error(f"读取数据库配置时出错: {e}. 请检查您的 Streamlit secrets 配置。")
        return None

# --- Initialization (Not cached, runs once or rarely) ---
def init_db():
    conn = get_db_connection() # Uses cached connection if available
    if conn is None:
        st.error("无法初始化数据库：数据库连接失败。")
        return
    cursor = None # Initialize cursor to None
    try:
        cursor = conn.cursor()
        # Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(20) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(100) NOT NULL,
                role VARCHAR(10) NOT NULL DEFAULT 'user',
                must_change_password_on_next_login BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Bookings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                booking_date DATE NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                attendees INT,
                purpose TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
    except Error as e:
        st.error(f"初始化数据库表时出错: {e}")
    finally:
        if cursor:
            cursor.close()
        # Do NOT close the connection `conn` here if it's from @st.cache_resource

def create_initial_admin_if_not_exists(student_id, password, name):
    conn = get_db_connection() # Uses cached connection
    if conn is None: return
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE student_id = %s AND role = 'admin'", (student_id,))
        if cursor.fetchone() is None:
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (student_id, password_hash, name, role) VALUES (%s, %s, %s, 'admin')",
                (student_id, hashed_password, name)
            )
            conn.commit()
            st.success(f"初始管理员 '{name}' ({student_id}) 创建成功。")
    except Error as e:
        st.error(f"创建初始管理员时出错: {e}")
    finally:
        if cursor:
            cursor.close()
        # Do NOT close conn

# --- User CRUD ---
@st.cache_data(ttl=300) # Cache user data for 5 minutes
def get_user_by_student_id_db(student_id):
    # st.write(f"DEBUG: DB Fetch - get_user_by_student_id_db({student_id})")
    conn = get_db_connection()
    if not conn: return None
    cursor = None
    user = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE student_id = %s", (student_id,))
        user = cursor.fetchone()
    except Error as e:
        st.error(f"DB: 获取用户(学号)失败: {e}")
    finally:
        if cursor: cursor.close()
    return user

@st.cache_data(ttl=300)
def get_user_by_id_db(user_id): # Primarily for fetching password_hash
    # st.write(f"DEBUG: DB Fetch - get_user_by_id_db({user_id})")
    conn = get_db_connection()
    if not conn: return None
    cursor = None
    user_data = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
    except Error as e:
        st.error(f"DB: 获取用户(ID)密码信息失败: {e}")
    finally:
        if cursor: cursor.close()
    return user_data

def update_user_password_db(user_id, new_password_hash):
    # Clear relevant caches before modifying data
    get_user_by_id_db.clear() # User whose password changed
    # Potentially clear other user-related caches if necessary
    # get_user_by_student_id_db.clear() # If student_id is derived from user_id elsewhere

    conn = get_db_connection()
    if not conn: return False
    cursor = None
    success = False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = %s, must_change_password_on_next_login = FALSE WHERE id = %s",
            (new_password_hash, user_id)
        )
        conn.commit()
        success = True
    except Error as e:
        st.error(f"DB: 更新密码失败: {e}")
    finally:
        if cursor: cursor.close()
    return success

@st.cache_data(ttl=300)
def get_all_users_db():
    # st.write("DEBUG: DB Fetch - get_all_users_db()")
    conn = get_db_connection()
    if not conn: return []
    cursor = None
    users = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, student_id, name, role, must_change_password_on_next_login FROM users ORDER BY name")
        users = cursor.fetchall()
    except Error as e:
        st.error(f"DB: 获取所有用户失败: {e}")
    finally:
        if cursor: cursor.close()
    return users

def add_user_db(student_id, name, password_hash, role):
    get_all_users_db.clear()
    # If get_user_by_student_id_db might be called immediately after for this new user:
    # get_user_by_student_id_db.clear() # Or pass args to clear specific entry if API supports

    conn = get_db_connection()
    if not conn: return False
    cursor = None
    success = False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (student_id, name, password_hash, role, must_change_password_on_next_login) VALUES (%s, %s, %s, %s, TRUE)",
            (student_id, name, password_hash, role)
        )
        conn.commit()
        success = True
    except Error as e:
        if e.errno == 1062:
             st.error(f"学号 '{student_id}' 已被注册。")
        else:
            st.error(f"DB: 添加用户失败: {e}")
    finally:
        if cursor: cursor.close()
    return success

def delete_user_db(user_id):
    get_all_users_db.clear()
    get_user_by_id_db.clear()
    # get_user_by_student_id_db.clear() # If it could have cached the deleted user

    conn = get_db_connection()
    if not conn: return False
    cursor = None
    success = False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        success = True
    except Error as e:
        st.error(f"DB: 删除用户失败: {e}")
    finally:
        if cursor: cursor.close()
    return success

def update_user_role_db(user_id, new_role):
    get_all_users_db.clear() # Role change affects the list display
    get_user_by_id_db.clear() # Potentially if role is part of user detail fetched by ID elsewhere
    # get_user_by_student_id_db.clear()

    conn = get_db_connection()
    if not conn: return False
    cursor = None
    success = False
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        conn.commit()
        success = True
    except Error as e:
        st.error(f"DB: 更新用户角色失败: {e}")
    finally:
        if cursor: cursor.close()
    return success

def reset_user_password_db(user_id, new_password_hash):
    get_user_by_id_db.clear() # Password hash changed
    get_all_users_db.clear() # must_change_password_on_next_login changed

    conn = get_db_connection()
    if not conn: return False
    cursor = None
    success = False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = %s, must_change_password_on_next_login = TRUE WHERE id = %s",
            (new_password_hash, user_id)
        )
        conn.commit()
        success = True
    except Error as e:
        st.error(f"DB: 重置密码失败: {e}")
    finally:
        if cursor: cursor.close()
    return success

# --- Booking CRUD ---
@st.cache_data(ttl=60) # Cache booking data for 1 minute
def get_bookings_for_date_db(booking_date):
    # st.write(f"DEBUG: DB Fetch - get_bookings_for_date_db({booking_date})")
    conn = get_db_connection()
    if not conn: return []
    cursor = None
    bookings = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.start_time, b.end_time, u.name as user_name, u.student_id, b.attendees, b.purpose
            FROM bookings b JOIN users u ON b.user_id = u.id
            WHERE b.booking_date = %s ORDER BY b.start_time
        """, (booking_date,))
        bookings = cursor.fetchall()
    except Error as e:
        st.error(f"DB: 获取当日预约失败: {e}")
    finally:
        if cursor: cursor.close()
    return bookings

@st.cache_data(ttl=60)
def get_bookings_filtered_db(display_start_date, user_id_to_filter=None):
    # st.write(f"DEBUG: DB Fetch - get_bookings_filtered_db(start={display_start_date}, user={user_id_to_filter})")
    conn = get_db_connection()
    if not conn: return []
    cursor = None
    bookings = []
    query = """
        SELECT b.id, b.booking_date, b.start_time, b.end_time, u.name as user_name, u.student_id, b.attendees, b.purpose
        FROM bookings b JOIN users u ON b.user_id = u.id
        WHERE b.booking_date >= %s
    """
    params = [display_start_date]

    if user_id_to_filter:
        query += " AND b.user_id = %s"
        params.append(user_id_to_filter)
    query += " ORDER BY b.booking_date DESC, b.start_time ASC"
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, tuple(params))
        bookings = cursor.fetchall()
    except Error as e:
        st.error(f"DB: 获取预约列表失败: {e}")
    finally:
        if cursor: cursor.close()
    return bookings

def create_booking_db(user_id, booking_date, start_time, end_time, attendees, purpose):
    # Clear caches that would be affected
    get_bookings_for_date_db.clear() # Could clear with args if API supports: (booking_date,)
    get_bookings_filtered_db.clear()

    conn = get_db_connection()
    if not conn: return False
    cursor = None
    success = False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO bookings (user_id, booking_date, start_time, end_time, attendees, purpose) VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, booking_date, start_time, end_time, attendees, purpose)
        )
        conn.commit()
        success = True
    except Error as e:
        st.error(f"DB: 创建预约失败: {e}")
    finally:
        if cursor: cursor.close()
    return success

def delete_booking_db(booking_id):
    get_bookings_for_date_db.clear() # Could be more specific if we knew the date
    get_bookings_filtered_db.clear()

    conn = get_db_connection()
    if not conn: return False
    cursor = None
    success = False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
        conn.commit()
        success = True
    except Error as e:
        st.error(f"DB: 删除预约失败: {e}")
    finally:
        if cursor: cursor.close()
    return success

def update_booking_db(booking_id, booking_date, start_time, end_time, attendees, purpose):
    get_bookings_for_date_db.clear() # Could be more specific
    get_bookings_filtered_db.clear()

    conn = get_db_connection()
    if not conn: return False
    cursor = None
    success = False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bookings SET booking_date=%s, start_time=%s, end_time=%s, attendees=%s, purpose=%s
            WHERE id=%s
        """, (booking_date, start_time, end_time, attendees, purpose, booking_id))
        conn.commit()
        success = True
    except Error as e:
        st.error(f"DB: 更新预约失败: {e}")
    finally:
        if cursor: cursor.close()
    return success

# Not caching this function to always get the latest conflict status before a write
def check_booking_conflict_db(booking_date, start_time, end_time, exclude_booking_id=None):
    # st.write(f"DEBUG: DB Check - check_booking_conflict_db({booking_date}, {start_time}, {end_time})")
    conn = get_db_connection()
    if not conn: return True # Assume conflict on DB error
    cursor = None
    conflicts = []
    query = """
        SELECT b.id, u.name as user_name, u.student_id, b.start_time, b.end_time, b.purpose
        FROM bookings b JOIN users u ON b.user_id = u.id
        WHERE b.booking_date = %s AND (
            (%s < b.end_time AND %s > b.start_time) 
        )
    """ 
    params = [booking_date, start_time, end_time]

    if exclude_booking_id:
        query += " AND b.id != %s"
        params.append(exclude_booking_id)
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, tuple(params))
        conflicts = cursor.fetchall()
    except Error as e:
        st.error(f"DB: 检查冲突失败: {e}")
        return True # Assume conflict on DB error
    finally:
        if cursor: cursor.close()
    return conflicts