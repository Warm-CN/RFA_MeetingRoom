# ui_pages/manage_bookings.py
import streamlit as st
import pandas as pd
from datetime import date, time, timedelta, datetime
from database_utils import (
    get_bookings_filtered_db, 
    delete_booking_db, 
    update_booking_db,
    check_booking_conflict_db
)
from utils import convert_db_time_to_datetime_time

def show_manage_bookings_page(show_all=False):
    user_id_to_filter = None if show_all else st.session_state.get('user_id')
    title = "所有预约记录" if show_all else "我的预约记录"
    st.subheader(title)

    if not user_id_to_filter and not show_all:
        st.warning("无法获取用户ID，请重新登录。")
        return

    today = date.today()
     # Change display_start_date to today to only show today and future bookings
    display_start_date = today # Only show today and future bookings

    bookings_raw = get_bookings_filtered_db(display_start_date, user_id_to_filter)
    
    future_and_current_bookings = []
    if bookings_raw:
        current_time_now = datetime.now().time()
        for b_item in bookings_raw:
            booking_item_date = b_item['booking_date']
            
            end_time_item = b_item['end_time']
            if isinstance(end_time_item, timedelta):
                 hours, remainder = divmod(end_time_item.seconds, 3600)
                 minutes, _ = divmod(remainder, 60)
                 end_time_item = time(hours, minutes)
            elif isinstance(end_time_item, str):
                try:
                    end_time_item = datetime.strptime(end_time_item, '%H:%M:%S').time()
                except ValueError:
                    end_time_item = datetime.strptime(end_time_item, '%H:%M').time()

            if booking_item_date > today:
                future_and_current_bookings.append(b_item)
            elif booking_item_date == today and end_time_item > current_time_now:
                future_and_current_bookings.append(b_item)
        
    bookings_to_display = future_and_current_bookings

    if bookings_to_display:
        df_bookings = pd.DataFrame(bookings_to_display)
        
        # --- Format time columns for display ---
        if 'start_time' in df_bookings.columns:
            df_bookings['start_time_str'] = df_bookings['start_time'].apply( # Create new column for formatted string
                lambda t: t.strftime('%H:%M') if isinstance(t, time) 
                          else (datetime.min + t).strftime('%H:%M') if isinstance(t, timedelta) 
                          else str(t)
            )
        if 'end_time' in df_bookings.columns:
            df_bookings['end_time_str'] = df_bookings['end_time'].apply( # Create new column for formatted string
                lambda t: t.strftime('%H:%M') if isinstance(t, time) 
                          else (datetime.min + t).strftime('%H:%M') if isinstance(t, timedelta) 
                          else str(t)
            )
        # --- End of time formatting ---

        df_bookings_display = df_bookings.rename(columns={
            'id': 'ID', 'booking_date': '日期', 
            'start_time_str': '开始时间', # Use the formatted string column
            'end_time_str': '结束时间',   # Use the formatted string column
            'user_name': '预约人', 'student_id': '学号',
            'attendees': '人数', 'purpose': '备注/主题'
        })
        display_cols = ['ID', '日期', '开始时间', '结束时间', '预约人', '学号', '人数', '备注/主题']
        st.dataframe(df_bookings_display[display_cols], hide_index=True, use_container_width=True)

        st.markdown("---")
        st.subheader("管理选中的预约")
        
        booking_options_dict = {
            b['id']: f"ID: {b['id']} - {b['booking_date']} ({b['start_time_str']}) - {b['user_name']}" # Use formatted time
            for b in df_bookings.to_dict('records') # Use df_bookings which has original and str time
        }
        options_list = [""] + list(booking_options_dict.keys())

        selected_booking_id = st.selectbox(
            "选择预约进行操作", 
            options=options_list,
            format_func=lambda x: booking_options_dict.get(x, "请选择一个预约..."),
            key=f"manage_booking_select_v2_{'all' if show_all else 'my'}"
        )

        if selected_booking_id:
            # Find the original booking details from df_bookings for editing (need original time objects)
            selected_booking_details_orig = next((b for b in df_bookings.to_dict('records') if b['id'] == selected_booking_id), None)

            if selected_booking_details_orig:
                # ... (Delete Button logic remains the same) ...
                if st.button(f"删除预约 ID: {selected_booking_id}", key=f"del_btn_v2_{selected_booking_id}", type="primary"):
                    if delete_booking_db(selected_booking_id):
                        st.success(f"预约 ID: {selected_booking_id} 已成功删除。")
                        st.rerun()
                    else:
                        st.error("删除预约时发生数据库错误。")

                with st.expander(f"编辑预约 ID: {selected_booking_id}"):
                    with st.form(f"edit_booking_form_v2_{selected_booking_id}"):
                        # Use utility for time conversion with original time objects
                        default_start = convert_db_time_to_datetime_time(selected_booking_details_orig['start_time'])
                        default_end = convert_db_time_to_datetime_time(selected_booking_details_orig['end_time'], default_time=time(10,0))
                        
                        edit_min_date = date.today()
                        edit_max_date = date.today() + timedelta(days=6)

                        edit_b_date = st.date_input("新日期", value=selected_booking_details_orig['booking_date'], min_value=edit_min_date, max_value=edit_max_date, key=f"edit_date_v2_{selected_booking_id}")
                        edit_s_time = st.time_input("新开始时间", value=default_start, key=f"edit_start_v2_{selected_booking_id}", step=timedelta(minutes=30))
                        edit_e_time = st.time_input("新结束时间", value=default_end, key=f"edit_end_v2_{selected_booking_id}", step=timedelta(minutes=30))
                        edit_att = st.number_input("新使用人数", min_value=1, value=selected_booking_details_orig['attendees'], step=1, key=f"edit_att_v2_{selected_booking_id}")
                        edit_pur = st.text_area("新备注/主题", value=selected_booking_details_orig['purpose'], key=f"edit_pur_v2_{selected_booking_id}")
                        
                        submit_edit_button = st.form_submit_button("确认修改预约")

                        if submit_edit_button:
                            # ... (rest of your edit submit logic, ensure conflict check uses new times) ...
                            if edit_s_time >= edit_e_time:
                                st.error("结束时间必须晚于开始时间。")
                            else:
                                conflicts = check_booking_conflict_db(edit_b_date, edit_s_time, edit_e_time, exclude_booking_id=selected_booking_id)
                                if conflicts: # Check if list is not empty
                                    if isinstance(conflicts, bool) and conflicts is True: # DB error during check
                                        st.error("检查预约冲突时发生数据库错误，请重试。")
                                    else:
                                        st.error("修改后的时间段与现有预约冲突！")
                                else: # No conflict
                                    if update_booking_db(selected_booking_id, edit_b_date, edit_s_time, edit_e_time, edit_att, edit_pur):
                                        st.success(f"预约 ID: {selected_booking_id} 已成功修改。")
                                        st.rerun()
                                    else:
                                        st.error("修改预约时发生数据库错误。")
    else:
        st.info("没有未来的或今日未完成的预约记录。")