import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Partner Audit Dashboard", layout="wide")

# Replace with your actual Google Sheet ID
# (Found in your sheet URL: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit)
SHEET_ID = "YOUR_GOOGLE_SHEET_ID_HERE"

# --- DATA LOADERS ---
@st.cache_data(ttl=600)
def load_data():
    audits_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Weekly_Audits"
    df_audits = pd.read_csv(audits_url)
    
    users_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Users"
    df_users = pd.read_csv(users_url)
    
    return df_audits, df_users

try:
    df_audits, df_users = load_data()
except Exception as e:
    st.error("Error loading data from Google Sheets. Check your Sheet ID and sharing permissions.")
    st.stop()

# --- SESSION STATE FOR LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.session_state["user_branch"] = None

# --- LOGIN SCREEN ---
if not st.session_state["logged_in"]:
    st.title("Partner Dashboard Login")
    
    with st.form("login_form"):
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign In")
        
        if submit:
            user_match = df_users[df_users["Email"].str.lower() == email.strip().lower()]
            
            if not user_match.empty and str(user_match.iloc[0]["Password_Hash"]) == password.strip():
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = user_match.iloc[0]["Role"]
                st.session_state["user_branch"] = str(user_match.iloc[0]["Branch"])
                st.rerun()
            else:
                st.error("Invalid Email or Password")

# --- MAIN DASHBOARD ---
else:
    user_role = st.session_state["user_role"]
    user_branch = st.session_state["user_branch"]
    
    st.sidebar.title("Navigation")
    st.sidebar.write(f"Logged in as: **{user_role}**")
    
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()
        
    # --- ROW-LEVEL SECURITY FILTERING ---
    if user_role == "Admin":
        all_branches = ["ALL"] + sorted(df_audits["Branch"].dropna().unique().tolist())
        selected_branch = st.sidebar.selectbox("Select Branch Filter", all_branches)
    else:
        selected_branch = user_branch
        st.sidebar.info(f"Filtered for Branch: **{selected_branch}**")

    if selected_branch == "ALL":
        filtered_df = df_audits
    else:
        filtered_df = df_audits[df_audits["Branch"] == selected_branch]

    st.title("Partner Audit & Performance Dashboard")
    st.subheader(f"Viewing metrics for: {selected_branch}")
    
    # --- KPI METRICS ---
    col1, col2, col3 = st.columns(3)
    
    total_audits = len(filtered_df)
    fake_updates = len(filtered_df[filtered_df["Genuine/Fake"].astype(str).str.contains("Fake", case=False, na=False)])
    
    filtered_df["Penalty Amount"] = pd.to_numeric(filtered_df["Penalty Amount"], errors="coerce").fillna(0)
    total_penalty = filtered_df["Penalty Amount"].sum()
    
    col1.metric("Total Audited Cases", f"{total_audits:,}")
    col2.metric("Fake Updates Identified", f"{fake_updates:,}")
    col3.metric("Total Penalty Amount", f"₹{total_penalty:,.2f}")
    
    st.markdown("---")
    
    # --- VISUALIZATION ---
    st.subheader("Breaches by Product Category")
    if not filtered_df.empty:
        cat_counts = filtered_df["Product Sub Category"].value_counts().head(10)
        
        fig, ax = plt.subplots(figsize=(10, 4))
        cat_counts.plot(kind="bar", ax=ax, color="#2563eb")
        ax.set_ylabel("Count")
        ax.set_xlabel("Product Sub Category")
        plt.xticks(rotation=45, ha="right")
        st.pyplot(fig)
    else:
        st.warning("No records found for this branch.")

    # --- DATA TABLE ---
    st.subheader("Audit Records Detail")
    display_cols = ["Case ID", "Branch", "Genuine/Fake", "Brand", "Product Sub Category", "Penalty Amount"]
    available_cols = [c for c in display_cols if c in filtered_df.columns]
    
    st.dataframe(filtered_df[available_cols], use_container_width=True)
