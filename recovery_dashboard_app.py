import pandas as pd
import streamlit as st
import requests
from datetime import date, datetime, timedelta

# -----------------------------
# App Config
# -----------------------------
st.set_page_config(page_title="Monthly Recovery Dashboard", layout="wide")

# Google Sheet URL (CSV Export URL for reading)
GSHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1voQfFNkNlGijKLcnyMaiCHCOQ9ckGQAZsqwHxTxUzJM/export?format=csv"
# The original URL for your reference
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1voQfFNkNlGijKLcnyMaiCHCOQ9ckGQAZsqwHxTxUzJM/edit?usp=sharing"

DEPARTMENTS = ["Front Desk", "Reservations", "River Room", "Gem & Keystone", "Kitchen", "Housekeeping", "Recreation", "Golf", "Maintenance", "Spa", "Other"]
ISSUE_TYPES = ["Room Readiness/Cleanliness", "Maintenance", "Noise", "Billing", "Service Delay", "F&B Quality", "F&B Wait Time", "Pest/Environmental", "Reservation Error", "Amenity Missing", "Recreation Experience", "Other"]
RECOVERY_TYPES = ["Apology Only", "Replace/Redo", "Amenity", "F&B Comp", "Activity Waiver", "Rate Adjustment", "Partial Refund", "Full Refund", "Comp Night", "Upgrade", "Other"]
SEVERITY = ["Low", "Medium", "High", "Critical"]

# -----------------------------
# Simplified Google Sheets Helpers
# -----------------------------
@st.cache_data(ttl=60 ) # Cache for 1 minute
def load_data():
    try:
        # Read the sheet directly as a CSV
        data = pd.read_csv(GSHEET_CSV_URL)
        if data.empty:
            return pd.DataFrame(columns=["incident_date", "guest_name", "room", "department", "issue_type", "severity", "description", "recovery_type", "recovery_value", "follow_up_required", "owner", "created_at"])
        
        # Basic data cleaning
        data["incident_date"] = pd.to_datetime(data["incident_date"], errors='coerce').dt.date
        data["recovery_value"] = pd.to_numeric(data["recovery_value"], errors="coerce").fillna(0.0)
        data['id'] = data.index + 1
        return data
    except Exception as e:
        st.error(f"Error reading data: {e}")
        return pd.DataFrame()

def save_to_gsheets(new_row):
    st.info("To enable saving, please follow the 'Service Account' guide I provided. For now, you can view your data!")
    # In a professional setup, we would use a Service Account here.
    # For now, I've simplified the app so it doesn't crash.
    return False

# -----------------------------
# UI and Logic
# -----------------------------
st.title("Monthly Guest Recovery Dashboard")
df = load_data()

# Filters
today = date.today()
st.sidebar.header("Filters")
date_range = st.sidebar.date_input("Date range", value=(today.replace(day=1), today))
dept_filter = st.sidebar.multiselect("Department", options=DEPARTMENTS)

filtered = df.copy()
if not filtered.empty:
    if isinstance(date_range, tuple) and len(date_range) == 2:
        filtered = filtered[(filtered["incident_date"] >= date_range[0]) & (filtered["incident_date"] <= date_range[1])]
    if dept_filter:
        filtered = filtered[filtered["department"].isin(dept_filter)]

# Entry Form
with st.expander("➕ Log a new recovery incident"):
    st.warning("Note: Saving to Google Sheets requires a 'Service Account' for security. Please check the guide I provided to enable this feature!")
    with st.form("incident_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            incident_date = st.date_input("Incident date", value=today)
            department = st.selectbox("Department", DEPARTMENTS)
            issue_type = st.selectbox("Issue type", ISSUE_TYPES)
        with c2:
            severity = st.selectbox("Severity", SEVERITY)
            recovery_type = st.selectbox("Recovery type", RECOVERY_TYPES)
            recovery_value = st.number_input("Recovery value ($)", min_value=0.0)
        with c3:
            guest_name = st.text_input("Guest name")
            room = st.text_input("Room/Location")
            owner = st.text_input("Owner/MOD")

        description = st.text_area("Description")
        if st.form_submit_button("Save Incident"):
            st.error("Saving is currently disabled. Please follow the 'Service Account' guide to enable permanent storage!")

# Dashboard View
if not filtered.empty:
    st.metric("Total Incidents", len(filtered))
    st.dataframe(filtered, use_container_width=True)
else:
    st.info("No data found in your Google Sheet. Once you enable 'Service Account' saving, your logs will appear here!")
