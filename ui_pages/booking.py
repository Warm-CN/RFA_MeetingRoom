# ui_pages/booking.py
import streamlit as st
import pandas as pd
from datetime import date, time, timedelta, datetime # Ensure datetime is imported
from database_utils import check_booking_conflict_db, create_booking_db, get_bookings_for_date_db

def show_booking_page():
    st.subheader("预约会议室") # Main title for the page
    today = date.today()
    
    # Date range settings for the main date picker
    # Users can only select today or future dates, up to one week in advance.
    min_selectable_date = today
    max_selectable_date = today + timedelta(days=6)  # Can book up to one week (today + 6 days)

    # --- 1. Date Picker ---
    selected_display_date = st.date_input(
        "选择日期查看预约情况或进行新的预约", # Combined label
        min_value=min_selectable_date,
        max_value=max_selectable_date,
        value=min_selectable_date,        # Default to today
        key="booking_page_date_selector_v4" # Ensure unique key
    )
    
    st.markdown("---") # Separator

    # --- 2. Daily Summary for the Selected Date ---
    st.subheader(f"{selected_display_date.strftime('%Y-%m-%d')} 当日预约情况：")
    day_bookings = get_bookings_for_date_db(selected_display_date)
    if day_bookings:
        df_day_bookings = pd.DataFrame(day_bookings)
        
        # Format time columns for display
        if 'start_time' in df_day_bookings.columns:
            df_day_bookings['start_time'] = df_day_bookings['start_time'].apply(
                lambda t: t.strftime('%H:%M') if isinstance(t, time) 
                          else (datetime.min + t).strftime('%H:%M') if isinstance(t, timedelta) 
                          else str(t)
            )
        if 'end_time' in df_day_bookings.columns:
            df_day_bookings['end_time'] = df_day_bookings['end_time'].apply(
                lambda t: t.strftime('%H:%M') if isinstance(t, time) 
                          else (datetime.min + t).strftime('%H:%M') if isinstance(t, timedelta) 
                          else str(t)
            )

        df_display_summary = df_day_bookings.rename(columns={
            'start_time': '开始', 'end_time': '结束', 'user_name': '预约人', 
            'student_id': '学号', 'attendees': '人数', 'purpose': '备注'
        })
        display_summary_cols = ['开始', '结束', '预约人', '学号', '人数', '备注']
        # Use st.dataframe for better table rendering and potential scrolling
        st.dataframe(df_display_summary[display_summary_cols], hide_index=True, use_container_width=True)
    else:
        st.info(f"当日（{selected_display_date.strftime('%Y-%m-%d')}）暂无预约。")
    
    st.markdown("---") # Separator

    # --- 3. Booking Form Area for the Selected Date ---
    st.subheader(f"为日期 {selected_display_date.strftime('%Y-%m-%d')} 进行新的预约：")

    # The form is always for a valid future date because selected_display_date is constrained.
    # No need for `can_book_this_date` check to disable the form based on date itself.
    
    # Optional: Use columns to constrain the width of the form if desired
    # form_col, _ = st.columns([0.7, 0.3]) # Example: Form takes 70% of the width
    # with form_col: # If using columns, indent the form
    with st.form("booking_form_nav_v4"): # Ensure unique form key
        start_time_dt = st.time_input(
            "开始时间", 
            value=time(9,0), 
            key="book_start_time_nav_v4", 
            step=timedelta(minutes=30)
        )
        end_time_dt = st.time_input(
            "结束时间", 
            value=time(10,0), 
            key="book_end_time_nav_v4", 
            step=timedelta(minutes=30)
        )
        
        attendees = st.number_input("使用人数", min_value=1, value=1, step=1, key="book_attendees_nav_v4")
        purpose = st.text_area("备注", key="book_purpose_nav_v4", placeholder="例如：周会、调试设备等")
        
        submit_button = st.form_submit_button("提交预约")

        if submit_button:
            if start_time_dt >= end_time_dt:
                st.error("结束时间必须晚于开始时间。")
            else:
                conflicting_bookings = check_booking_conflict_db(selected_display_date, start_time_dt, end_time_dt)
                
                if conflicting_bookings:
                    if isinstance(conflicting_bookings, bool) and conflicting_bookings is True:
                        st.error("检查预约冲突时发生数据库错误，请稍后重试或联系管理员。")
                    else:
                        st.error("抱歉，您选择的时间段与以下已有预约冲突：")
                        for cb in conflicting_bookings:
                            cb_start_str = cb['start_time'].strftime('%H:%M') if isinstance(cb['start_time'], time) else str(cb['start_time'])
                            cb_end_str = cb['end_time'].strftime('%H:%M') if isinstance(cb['end_time'], time) else str(cb['end_time'])
                            st.error(f"- {cb_start_str} 至 {cb_end_str} (预约人: {cb['user_name']}, 学号: {cb['student_id']})")
                else: 
                    if 'user_id' not in st.session_state:
                        st.error("无法获取用户信息，请重新登录后再试。")
                    elif create_booking_db(st.session_state.user_id, selected_display_date, start_time_dt, end_time_dt, attendees, purpose):
                        st.success(
                            f"会议室于 {selected_display_date.strftime('%Y-%m-%d')} "
                            f"{start_time_dt.strftime('%H:%M')} - {end_time_dt.strftime('%H:%M')} "
                            f"预约成功！"
                        )
                        st.rerun() 
                    else:
                        st.error("预约未能成功保存，请检查输入或稍后再试。")