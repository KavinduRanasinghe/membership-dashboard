import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Set up page configuration
st.set_page_config(
    page_title="Membership Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, clean UI
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 5% 5% 5% 10%;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CONFIGURATION & STATE INITIALIZATION
# ==========================================
ADMIN_USERNAME = st.secrets["credentials"]["ADMIN_USERNAME"]
ADMIN_PASSWORD = st.secrets["credentials"]["ADMIN_PASSWORD"]

DEFAULT_CSV_PATH = r"ieee_sri_lanka_membership_sample.csv"

if "membership_data" not in st.session_state:
    if os.path.exists(DEFAULT_CSV_PATH):
        try:
            st.session_state["membership_data"] = pd.read_csv(DEFAULT_CSV_PATH)
        except Exception:
            st.session_state["membership_data"] = None
    else:
        st.session_state["membership_data"] = None

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
view_mode = st.sidebar.radio("Navigation", ["Dashboard", "Administration"])

st.sidebar.markdown("---")
st.sidebar.caption("Membership Analytics Platform v1.1")

# ==========================================
# ADMIN PANEL (SECURED)
# ==========================================
if view_mode == "Administration":
    st.header("System Administration")
    
    if not st.session_state["logged_in"]:
        st.markdown("Enter credentials to access the data management panel.")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Authenticate")
            
            if submitted:
                if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Authentication failed. Please check your credentials.")
                    
    else:
        col1, col2 = st.columns([8, 1])
        with col2:
            if st.button("Sign Out"):
                st.session_state["logged_in"] = False
                st.rerun()
                
        st.subheader("Data Management")
        
        if st.session_state["membership_data"] is not None:
            st.success("System status: Active dataset loaded.")
            
        uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"])
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                
                if df.empty or len(df.columns) < 2:
                    st.error("Invalid format. Ensure the file contains a University column and historical month columns.")
                else:
                    st.session_state["membership_data"] = df
                    st.success("Dataset successfully overwritten. View the Dashboard to see updates.")
                    
                    with st.expander("Dataset Preview"):
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
            except Exception as e:
                st.error(f"Processing error: {e}")
                
        if st.session_state["membership_data"] is not None:
            st.markdown("---")
            if st.button("Clear Active Dataset"):
                st.session_state["membership_data"] = None
                st.rerun()

# ==========================================
# USER DASHBOARD (PUBLIC)
# ==========================================
elif view_mode == "Dashboard":
    st.title("Membership Analytics")
    
    if st.session_state["membership_data"] is None:
        st.warning("No data source available. Please contact the administrator to initialize the dataset.")
        st.stop()
        
    df = st.session_state["membership_data"].copy()
    
    # Identify structures dynamically
    univ_col = df.columns[0]
    month_cols = list(df.columns[1:])
    
    if len(month_cols) < 2:
        st.error("At least two months of data are required to calculate growth trends.")
        st.stop()
        
    latest_month = month_cols[-1]
    prev_month = month_cols[-2]
    
    # Clean data (ensure membership counts are numeric)
    for col in month_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
    # Calculate Growth Data
    df["Growth"] = df[latest_month] - df[prev_month]
        
    # 1. Key Metrics
    st.subheader("Key Metrics")
    col1, col2, col3 = st.columns(3)
    
    total_latest_members = df[latest_month].sum()
    total_prev_members = df[prev_month].sum()
    total_growth = total_latest_members - total_prev_members
    
    top_univ = df.loc[df[latest_month].idxmax(), univ_col]
    top_univ_count = df[latest_month].max()
    top_univ_growth = df.loc[df[latest_month].idxmax(), "Growth"]
    
    with col1:
        st.metric(
            label=f"Total Members ({latest_month})", 
            value=f"{total_latest_members:,}",
            delta=f"{total_growth:,} vs {prev_month}"
        )
    with col2:
        st.metric(
            label="Highest Performing Branch", 
            value=str(top_univ)
        )
    with col3:
        st.metric(
            label="Peak Branch Volume", 
            value=f"{top_univ_count:,}",
            delta=f"{top_univ_growth:,} new members"
        )
        
    st.markdown("---")
    
    # 2. Leaderboard & Bar Chart
    left_layout, right_layout = st.columns([1, 1], gap="large")
    
    with left_layout:
        st.subheader(f"Current Standings: {latest_month}")
        
        # Sort dataframe by the latest month's data and include the Growth column
        leaderboard_df = df[[univ_col, latest_month, "Growth"]].sort_values(by=latest_month, ascending=False).reset_index(drop=True)
        leaderboard_df.index += 1  
        leaderboard_df.columns = ["Branch", "Active Members", f"Growth (vs {prev_month})"]
        
        st.dataframe(
            leaderboard_df, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "Active Members": st.column_config.NumberColumn(format="%d"),
                f"Growth (vs {prev_month})": st.column_config.NumberColumn(format="%+d") # The + forces a + or - sign
            }
        )
        
    with right_layout:
        st.subheader("Volume Distribution (Top 15)")
        
        fig_bar = px.bar(
            leaderboard_df.head(15), 
            x="Active Members",
            y="Branch",
            orientation='h',
            text="Active Members",
            color="Active Members",
            color_continuous_scale="Blues"
        )
        fig_bar.update_layout(
            yaxis={'categoryorder':'total ascending'},
            template='plotly_white',
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    st.markdown("---")
    
    # 3. Historical Trend Analysis
    st.subheader("Membership Progression")
    
    all_options = ["All Branches"] + list(df[univ_col].unique())
    
    selected_univs = st.multiselect(
        "Filter by Branch",
        options=all_options,
        default=["All Branches"] 
    )
    
    if selected_univs:
        if "All Branches" in selected_univs:
            filtered_df = df 
        else:
            filtered_df = df[df[univ_col].isin(selected_univs)]
            
        melted_df = filtered_df.melt(
            id_vars=[univ_col], 
            value_vars=month_cols, 
            var_name="Month", 
            value_name="Members"
        )
        
        fig_trend = px.line(
            melted_df,
            x="Month",
            y="Members",
            color=univ_col,
            markers=True
        )
        fig_trend.update_layout(
            template='plotly_white',
            legend_title_text='Branch',
            legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
            margin=dict(l=0, r=0, t=10, b=0)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Select a branch to view historical progression.")