import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Partner Audit Dashboard", layout="wide")

st.title("Partner Audit & Performance Dashboard")

# --- SIDEBAR FILE UPLOADERS ---
st.sidebar.header("📁 Load Data")
audit_file = st.sidebar.file_uploader("Upload Weekly Audits CSV", type=["csv"])
user_file = st.sidebar.file_uploader("Upload Users Credentials CSV", type=["csv"])

if not audit_file or not user_file:
    st.info("👈 Please upload both **Weekly Audits CSV** and **Users CSV** in the sidebar to view metrics.")
    st.stop()

# --- LOAD CSV DATA ---
@st.cache_data
def parse_uploaded_files(a_file, u_file):
    df_a = pd.read_csv(a_file)
    df_u = pd.read_csv(u_file)
    return df_a, df_u

try:
    df_audits, df_users = parse_uploaded_files(audit_file, user_file)
except Exception as e:
    st.error(f"Error parsing uploaded files: {e}")
    st.stop()

# --- SESSION STATE AUTHENTICATION ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.session_state["user_branch"] = None

# --- LOGIN SCREEN ---
if not st.session_state["logged_in"]:
    st.subheader("Partner Portal Login")
    
    with st.form("login_form"):
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign In")
        
        if submit:
            user_match = df_users[df_users["Email"].astype(str).str.lower() == email.strip().lower()]
            
            if not user_match.empty and str(user_match.iloc[0]["Password_Hash"]) == password.strip():
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = user_match.iloc[0]["Role"]
                st.session_state["user_branch"] = str(user_match.iloc[0]["Branch"])
                st.rerun()
            else:
                st.error("Invalid Email or Password")

# --- MAIN DASHBOARD VIEW ---
else:
    user_role = st.session_state["user_role"]
    user_branch = st.session_state["user_branch"]
    
    st.sidebar.markdown("---")
    st.sidebar.write(f"Logged in as: **{user_role}**")
    
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()
        
    # --- ROW-LEVEL SECURITY FILTERING ---
    if user_role == "Admin":
        all_branches = ["ALL"] + sorted(df_audits["Branch"].dropna().astype(str).unique().tolist())
        selected_branch = st.sidebar.selectbox("Select Branch Filter", all_branches)
    else:
        selected_branch = user_branch
        st.sidebar.info(f"Filtered for Branch: **{selected_branch}**")

    # Apply RLS Filter
    if selected_branch == "ALL":
        filtered_df = df_audits
    else:
        filtered_df = df_audits[df_audits["Branch"].astype(str) == selected_branch]

    st.subheader(f"Viewing metrics for: {selected_branch}")
    
    # --- KPI CARDS ---
    col1, col2, col3 = st.columns(3)
    
    total_audits = len(filtered_df)
    fake_updates = len(filtered_df[filtered_df["Genuine/Fake"].astype(str).str.contains("Fake", case=False, na=False)])
    
    filtered_df["Penalty Amount"] = pd.to_numeric(filtered_df["Penalty Amount"], errors="coerce").fillna(0)
    total_penalty = filtered_df["Penalty Amount"].sum()
    
    col1.metric("Total Audited Cases", f"{total_audits:,}")
    col2.metric("Fake Updates Identified", f"{fake_updates:,}")
    col3.metric("Total Penalty Amount", f"₹{total_penalty:,.2f}")
    
    st.markdown("---")
    
    # --- CHART ---
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
