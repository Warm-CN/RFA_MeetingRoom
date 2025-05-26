# utils.py
from datetime import datetime, timedelta, time
# import streamlit as st # Only if st.error/warning is used directly here

def convert_db_time_to_datetime_time(db_time_value, default_time=time(9,0), field_name="time"):
    """
    Converts a time value retrieved from the database (potentially timedelta or string)
    to a datetime.time object suitable for st.time_input.
    """
    if isinstance(db_time_value, timedelta):
        hours, remainder = divmod(db_time_value.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return time(hours, minutes)
    elif isinstance(db_time_value, str):
        try:
            return datetime.strptime(db_time_value, '%H:%M:%S').time()
        except ValueError:
            try:
                return datetime.strptime(db_time_value, '%H:%M').time()
            except ValueError:
                # Consider logging instead of direct st.error for a util function
                # print(f"Error parsing {field_name}: {db_time_value}")
                return default_time
    elif isinstance(db_time_value, time):
        return db_time_value
    else:
        # print(f"Unknown {field_name} format: {type(db_time_value)}. Using default.")
        return default_time