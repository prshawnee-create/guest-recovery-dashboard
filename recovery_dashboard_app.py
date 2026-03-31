import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# -----------------------------
# App Config
# -----------------------------
st.set_page_config(page_title="Monthly Recovery Dashboard", layout="wide")

# Google Sheet URL
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1voQfFNkNlGijKLcnyMaiCHCOQ9ckGQAZsqwHxTxUzJM/edit?usp=sharing"

DEPARTMENTS = ["Front Desk", "Reservations", "River Room", "Gem & Keystone", "Kitchen", "Housekeeping", "Recreation", "Golf", "Maintenance", "Spa", "Other"]
ISSUE_TYPES = ["Room Readiness/Cleanliness", "Maintenance", "Noise", "Billing", "Service Delay", "F&B Quality", "F&B Wait Time", "Pest/Environmental", "Reservation Error", "Amenity Missing", "Recreation Experience", "Other"]
RECOVERY_TYPES = ["Apology Only", "Replace/Redo", "Amenity", "F&B Comp", "Activity Waiver", "Rate Adjustment", "Partial Refund", "Full Refund", "Comp Night", "Upgrade", "Other"]
SEVERITY = ["Low", "Medium", "High", "Critical"]

# -----------------------------
# Smart Google Sheets Helpers
# -----------------------------
@st.cache_data(ttl=300 )
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Read the sheet - we don't specify columns so it doesn't crash if they change
        data = conn.read(spreadsheet=GSHEET_URL, worksheet="Sheet1", ttl=0)
        
        if data is None or data.empty:
            # If empty, create a fresh dataframe with the correct headers
            return pd.DataFrame(columns=["incident_date", "guest_name", "room", "department", "issue_type", "severity", "description", "recovery_type", "recovery_value", "follow_up_required", "owner", "root_cause", "corrective_action", "created_at", "id"])

        # Add an 'id' column based on row index for the dashboard to use
        data['id'] = data.index + 1
        
        # Basic data cleaning
        if "incident_date" in data.columns:
            data["incident_date"] = pd.to_datetime(data["incident_date"], errors='coerce').dt.date
        if "recovery_value" in data.columns:
            data["recovery_value"] = pd.to_numeric(data["recovery_value"], errors="coerce").fillna(0.0)
        
        return data
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

def save_to_gsheets(df_to_save):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Drop the helper 'id' column before saving back
        df_final = df_to_save.drop(columns=['id']) if 'id' in df_to_save.columns else df_to_save
        
        # Update the sheet
        conn.update(spreadsheet=GSHEET_URL, worksheet="Sheet1", data=df_final)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Save Error: {e}")
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
if not filtered.empty and "incident_date" in filtered.columns:
    if isinstance(date_range, tuple) and len(date_range) == 2:
        filtered = filtered[(filtered["incident_date"] >= date_range[0]) & (filtered["incident_date"] <= date_range[1])]
    if dept_filter:
        filtered = filtered[filtered["department"].isin(dept_filter)]

# Entry Form
with st.expander("➕ Log a new recovery incident"):
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
        follow_up = st.checkbox("Follow-up required")
        
        if st.form_submit_button("Save Incident"):
            new_row = {
                "incident_date": incident_date.isoformat(),
                "guest_name": guest_name,
                "room": room,
                "department": department,
                "issue_type": issue_type,
                "severity": severity,
                "description": description,
                "recovery_type": recovery_type,
                "recovery_value": recovery_value,
                "follow_up_required": str(follow_up),
                "owner": owner,
                "created_at": datetime.now().isoformat()
            }
            # Append and Save
            updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            if save_to_gsheets(updated_df):
                st.success("Saved!")
                st.rerun()

# Dashboard View
if not filtered.empty:
    st.metric("Total Incidents", len(filtered))
    st.dataframe(filtered, use_container_width=True)
else:
    st.info("No data found. Log your first incident above!")
