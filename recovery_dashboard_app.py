import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# -----------------------------
# App Config
# -----------------------------
st.set_page_config(page_title="Monthly Recovery Dashboard", layout="wide")

# Google Sheet URL provided by the user
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1voQfFNkNlGijKLcnyMaiCHCOQ9ckGQAZsqwHxTxUzJM/edit?usp=sharing"

DEPARTMENTS = [
    "Front Desk", "Reservations", "River Room", "Gem & Keystone", "Kitchen",
    "Housekeeping", "Recreation", "Golf", "Maintenance", "Spa", "Other"
]

ISSUE_TYPES = [
    "Room Readiness/Cleanliness", "Maintenance", "Noise", "Billing", "Service Delay",
    "F&B Quality", "F&B Wait Time", "Pest/Environmental", "Reservation Error",
    "Amenity Missing", "Recreation Experience", "Other"
]

RECOVERY_TYPES = [
    "Apology Only", "Replace/Redo", "Amenity", "F&B Comp", "Activity Waiver",
    "Rate Adjustment", "Partial Refund", "Full Refund", "Comp Night", "Upgrade", "Other"
]

SEVERITY = ["Low", "Medium", "High", "Critical"]


# -----------------------------
# Google Sheets Helpers
# -----------------------------
@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(spreadsheet=GSHEET_URL, worksheet="Sheet1", usecols=list(range(14)), ttl=5)
    
    # Check if data is empty or only contains headers
    if data.empty:
        return pd.DataFrame(columns=[
            "incident_date", "guest_name", "room", "department", "issue_type", "severity",
            "description", "recovery_type", "recovery_value", "follow_up_required",
            "owner", "root_cause", "corrective_action", "created_at", "id"
        ])

    # Ensure correct column names
    data.columns = [
        "incident_date", "guest_name", "room", "department", "issue_type", "severity",
        "description", "recovery_type", "recovery_value", "follow_up_required",
        "owner", "root_cause", "corrective_action", "created_at"
    ]

    # Ensure correct data types
    data["incident_date"] = pd.to_datetime(data["incident_date"]).dt.date
    data["created_at"] = pd.to_datetime(data["created_at"])
    data["recovery_value"] = pd.to_numeric(data["recovery_value"], errors="coerce").fillna(0.0)
    data["follow_up_required"] = data["follow_up_required"].astype(str).str.lower().isin(['true', '1', 'yes'])
    
    # Add an 'id' column based on row index
    data['id'] = data.index + 1 
    return data

def append_incident(row_data: dict):
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Convert boolean to string for Google Sheets
    row_data["follow_up_required"] = str(row_data["follow_up_required"])
    # Convert to DataFrame for appending
    df_to_append = pd.DataFrame([row_data])
    conn.create(spreadsheet=GSHEET_URL, worksheet="Sheet1", data=pd.concat([load_data().drop(columns=['id']), df_to_append], ignore_index=True))
    st.cache_data.clear()

def delete_incident_from_gsheets(incident_id: int):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = load_data()
    if not df.empty and incident_id in df['id'].values:
        # Filter out the row to delete
        df_updated = df[df['id'] != incident_id].drop(columns=['id'])
        
        # Format dates back to string for GSheets
        df_updated["incident_date"] = df_updated["incident_date"].apply(lambda x: x.isoformat() if isinstance(x, date) else x)
        df_updated["created_at"] = df_updated["created_at"].apply(lambda x: x.isoformat() if isinstance(x, datetime) else x)
        df_updated["follow_up_required"] = df_updated["follow_up_required"].astype(str)

        # Overwrite the sheet with the updated data
        conn.create(spreadsheet=GSHEET_URL, worksheet="Sheet1", data=df_updated)
        st.cache_data.clear()
    else:
        st.warning(f"Incident ID {incident_id} not found.")


# -----------------------------
# KPI Helpers
# -----------------------------
def month_bounds(d: date):
    first = d.replace(day=1)
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1, day=1)
    else:
        next_first = first.replace(month=first.month + 1, day=1)
    last = next_first - timedelta(days=1)
    return first, last

def top_repeats(df: pd.DataFrame, window_days=30, threshold=2):
    if df.empty:
        return pd.DataFrame(columns=["issue_type", "count"])
    cutoff = date.today() - timedelta(days=window_days)
    recent = df[df["incident_date"] >= cutoff]
    if recent.empty:
        return pd.DataFrame(columns=["issue_type", "count"])
    counts = recent.groupby("issue_type")["id"].count().sort_values(ascending=False).reset_index()
    counts.columns = ["issue_type", "count"]
    return counts[counts["count"] >= threshold]

# -----------------------------
# UI Layout
# -----------------------------
st.title("Monthly Guest Recovery Dashboard")
st.caption("Log incidents, track recovery cost, spot repeat issues, and close the loop.")

# -----------------------------
# Sidebar Filters
# -----------------------------
df = load_data()

today = date.today()
default_start, default_end = month_bounds(today)
default_end = min(default_end, today)

st.sidebar.header("Filters")
date_range = st.sidebar.date_input(
    "Date range",
    value=(default_start, default_end),
    min_value=date(2020, 1, 1),
    max_value=today
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = default_start, default_end

dept_filter = st.sidebar.multiselect("Department", options=DEPARTMENTS, default=[])
issue_filter = st.sidebar.multiselect("Issue type", options=ISSUE_TYPES, default=[])

filtered = df.copy()
if not filtered.empty:
    filtered = filtered[(filtered["incident_date"] >= start_date) & (filtered["incident_date"] <= end_date)]
    if dept_filter:
        filtered = filtered[filtered["department"].isin(dept_filter)]
    if issue_filter:
        filtered = filtered[filtered["issue_type"].isin(issue_filter)]

# -----------------------------
# Entry Form
# -----------------------------
with st.expander("➕ Log a new recovery incident", expanded=False):
    with st.form("incident_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            incident_date = st.date_input("Incident date", value=today)
            department = st.selectbox("Department", DEPARTMENTS, index=0)
            issue_type = st.selectbox("Issue type", ISSUE_TYPES, index=0)
        with c2:
            severity = st.selectbox("Severity", SEVERITY, index=1)
            recovery_type = st.selectbox("Recovery type", RECOVERY_TYPES, index=0)
            recovery_value = st.number_input("Recovery value ($)", min_value=0.0, step=5.0, value=0.0)
        with c3:
            guest_name = st.text_input("Guest name (optional)")
            room = st.text_input("Room / Table / Location (optional)")
            owner = st.text_input("Owner (manager / MOD) (optional)")

        description = st.text_area("What happened? (short description)", height=90)
        follow_up_required = st.checkbox("Follow-up required", value=False)
        root_cause = st.text_input("Root cause (optional)")
        corrective_action = st.text_input("Corrective action / prevention (optional)")

        submitted = st.form_submit_button("Save incident")
        if submitted:
            append_incident({
                "incident_date": incident_date.isoformat(),
                "guest_name": guest_name.strip() if guest_name else "",
                "room": room.strip() if room else "",
                "department": department,
                "issue_type": issue_type,
                "severity": severity,
                "description": description.strip() if description else "",
                "recovery_type": recovery_type,
                "recovery_value": float(recovery_value),
                "follow_up_required": bool(follow_up_required),
                "owner": owner.strip() if owner else "",
                "root_cause": root_cause.strip() if root_cause else "",
                "corrective_action": corrective_action.strip() if corrective_action else "",
                "created_at": datetime.now().isoformat(timespec="seconds")
            })
            st.success("Incident saved to Google Sheet.")
            st.rerun()

# -----------------------------
# KPIs
# -----------------------------
k1, k2, k3, k4 = st.columns(4)

incident_count = int(filtered["id"].nunique()) if not filtered.empty else 0
total_cost = float(filtered["recovery_value"].sum()) if not filtered.empty else 0.0
avg_cost = float(filtered["recovery_value"].mean()) if not filtered.empty else 0.0
followups = int(filtered["follow_up_required"].sum()) if not filtered.empty else 0

k1.metric("Incidents", f"{incident_count}")
k2.metric("Total Recovery Cost", f"${total_cost:,.2f}")
k3.metric("Avg Cost / Incident", f"${avg_cost:,.2f}")
k4.metric("Follow-ups Required", f"{followups}")

st.divider()

# -----------------------------
# Charts & Insights
# -----------------------------
left, right = st.columns([1.2, 0.8])

with left:
    st.subheader("Trends")
    if filtered.empty:
        st.info("No incidents in the selected date range yet.")
    else:
        # Incidents by day
        by_day = (
            filtered.groupby("incident_date")["id"].count()
            .reset_index(name="incidents")
            .sort_values("incident_date")
        )
        st.line_chart(by_day, x="incident_date", y="incidents")

        # Incidents by department
        by_dept = (
            filtered.groupby("department")["id"].count()
            .reset_index(name="incidents")
            .sort_values("incidents", ascending=False)
        )
        st.bar_chart(by_dept, x="department", y="incidents")

with right:
    st.subheader("Repeat Issues (last 30 days)")
    repeats = top_repeats(df, window_days=30, threshold=2)
    if repeats.empty:
        st.success("No repeat issue types above the threshold in the last 30 days.")
    else:
        st.dataframe(repeats, use_container_width=True, hide_index=True)

    st.subheader("Cost Drivers")
    if filtered.empty:
        st.write("—")
    else:
        by_issue_cost = (
            filtered.groupby("issue_type")["recovery_value"].sum()
            .reset_index(name="total_cost")
            .sort_values("total_cost", ascending=False)
            .head(8)
        )
        st.bar_chart(by_issue_cost, x="issue_type", y="total_cost")

st.divider()

# -----------------------------
# Data Table + Export + Delete
# -----------------------------
st.subheader("Incidents (filtered)")
if filtered.empty:
    st.write("No records to display.")
else:
    show_cols = [
        "id", "incident_date", "department", "issue_type", "severity",
        "recovery_type", "recovery_value", "follow_up_required", "owner",
        "guest_name", "room", "description", "root_cause", "corrective_action"
    ]
    st.dataframe(filtered[show_cols].sort_values(["incident_date", "id"], ascending=[False, False]),
                 use_container_width=True, hide_index=True)

    csv = filtered[show_cols].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", data=csv, file_name="recovery_dashboard_export.csv", mime="text/csv")

    with st.expander("🗑️ Delete a record (admin)"):
        incident_id = st.number_input("Incident ID to delete", min_value=1, step=1)
        if st.button("Delete"):
            delete_incident_from_gsheets(int(incident_id))
            st.warning(f"Deleted incident ID {incident_id} from Google Sheet.")
            st.rerun()
