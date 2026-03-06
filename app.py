import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Giv Development Dashboard",
    layout="wide"
)

st.title("Development Pipeline Dashboard")

# ----------------------------
# Load Data
# ----------------------------

projects = pd.read_csv("PROJECTS.csv")
people = pd.read_csv("PEOPLE.csv")

# Convert date columns

date_columns = [col for col in projects.columns if "Start" in col or "End" in col]

for col in date_columns:
    projects[col] = pd.to_datetime(projects[col], errors="coerce")

# ----------------------------
# Filters
# ----------------------------

st.sidebar.header("Filters")

company_filter = st.sidebar.multiselect(
    "Company",
    projects["Company"].dropna().unique()
)

lead_filter = st.sidebar.multiselect(
    "Lead Developer",
    projects["Lead Developer"].dropna().unique()
)

filtered_projects = projects.copy()

if company_filter:
    filtered_projects = filtered_projects[
        filtered_projects["Company"].isin(company_filter)
    ]

if lead_filter:
    filtered_projects = filtered_projects[
        filtered_projects["Lead Developer"].isin(lead_filter)
    ]

# ----------------------------
# Build Timeline Table
# ----------------------------

timeline_rows = []

phase_columns = [
    ("Precon / Architectural", "Precon/Architectural Start", "Precon/Architectural End"),
    ("LIHTC Application", "LIHTC App Start", "LIHTC App End"),
    ("4% Application", "4% App Start", "4% App End"),
    ("Zoning", "Zoning Start", "Zoning End"),
    ("Permitting", "Permitting Start", "Permitting End"),
    ("Sales", "Sales Start", "Sales End"),
    ("Construction", "Construction Start", "Construction End"),
    ("Stabilization / 8609", "Conversion/Stabilization/8609 Start", "Conversion/Stabilization/8609 End"),
]

for _, row in filtered_projects.iterrows():

    for phase_name, start_col, end_col in phase_columns:

        start = row.get(start_col)
        end = row.get(end_col)

        if pd.notna(start) and pd.notna(end):

            timeline_rows.append({
                "Project": row["Project Name"],
                "Phase": phase_name,
                "Start": start,
                "End": end,
                "Company": row["Company"],
                "Lead Developer": row["Lead Developer"],
                "Assistant": row["Asst Developer"]
            })

timeline_df = pd.DataFrame(timeline_rows)

# ----------------------------
# Timeline Visualization
# ----------------------------

st.header("Project Timeline")

if len(timeline_df) > 0:

    fig = px.timeline(
        timeline_df,
        x_start="Start",
        x_end="End",
        y="Project",
        color="Phase",
        hover_data=["Company", "Lead Developer", "Assistant"]
    )

    fig.update_yaxes(autorange="reversed")

    st.plotly_chart(fig, use_container_width=True)

else:

    st.warning("No timeline data available with current filters")

# ----------------------------
# Raw Data (optional)
# ----------------------------

with st.expander("Project Data"):
    st.dataframe(filtered_projects)

with st.expander("People Data"):
    st.dataframe(people)
