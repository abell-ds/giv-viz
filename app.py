import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Giv Development Dashboard", layout="wide")
st.title("Development Pipeline Dashboard")

# ----------------------------
# Helpers
# ----------------------------

def read_csv_flexible(path_str):
    path = Path(path_str)
    if not path.exists():
        st.error(f"File not found: {path_str}")
        return pd.DataFrame()

    # Try common separators
    for sep in [",", ";", "\t", "|"]:
        try:
            df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
            # If we got more than 1 column, this separator probably worked
            if df.shape[1] > 1:
                return clean_columns(df)
        except Exception:
            pass

    # Final fallback
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
        return clean_columns(df)
    except Exception as e:
        st.error(f"Could not read {path_str}: {e}")
        return pd.DataFrame()

def clean_columns(df):
    df.columns = [str(c).strip() for c in df.columns]
    return df

def safe_to_datetime(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

# ----------------------------
# Load Data
# ----------------------------

projects = read_csv_flexible("PROJECTS.csv")
people = read_csv_flexible("PEOPLE.csv")

st.subheader("Debug: Loaded Files")

c1, c2 = st.columns(2)
with c1:
    st.write("**PROJECTS.csv shape**", projects.shape)
    st.write("**PROJECTS.csv columns**")
    st.write(list(projects.columns))

with c2:
    st.write("**PEOPLE.csv shape**", people.shape)
    st.write("**PEOPLE.csv columns**")
    st.write(list(people.columns))

if projects.empty:
    st.stop()

# ----------------------------
# Expected project columns
# ----------------------------

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

expected_project_cols = {
    "Project Name",
    "Company",
    "Lead Developer",
    "Asst Developer",
}

for _, start_col, end_col in phase_columns:
    expected_project_cols.add(start_col)
    expected_project_cols.add(end_col)

missing_cols = [c for c in expected_project_cols if c not in projects.columns]

if missing_cols:
    st.warning("Some expected columns were not found:")
    st.write(missing_cols)

# ----------------------------
# Parse dates
# ----------------------------

date_columns = [c for _, s, e in phase_columns for c in [s, e] if c in projects.columns]
projects = safe_to_datetime(projects, date_columns)

# ----------------------------
# Filters
# ----------------------------

st.sidebar.header("Filters")

company_options = sorted(projects["Company"].dropna().astype(str).unique()) if "Company" in projects.columns else []
lead_options = sorted(projects["Lead Developer"].dropna().astype(str).unique()) if "Lead Developer" in projects.columns else []

company_filter = st.sidebar.multiselect("Company", company_options)
lead_filter = st.sidebar.multiselect("Lead Developer", lead_options)

filtered_projects = projects.copy()

if company_filter and "Company" in filtered_projects.columns:
    filtered_projects = filtered_projects[filtered_projects["Company"].astype(str).isin(company_filter)]

if lead_filter and "Lead Developer" in filtered_projects.columns:
    filtered_projects = filtered_projects[filtered_projects["Lead Developer"].astype(str).isin(lead_filter)]

st.write("**Filtered project rows:**", len(filtered_projects))

# ----------------------------
# Build timeline
# ----------------------------

timeline_rows = []

for _, row in filtered_projects.iterrows():
    project_name = row["Project Name"] if "Project Name" in filtered_projects.columns else "Unknown Project"
    company = row["Company"] if "Company" in filtered_projects.columns else None
    lead = row["Lead Developer"] if "Lead Developer" in filtered_projects.columns else None
    assistant = row["Asst Developer"] if "Asst Developer" in filtered_projects.columns else None

    for phase_name, start_col, end_col in phase_columns:
        if start_col not in filtered_projects.columns or end_col not in filtered_projects.columns:
            continue

        start = row[start_col]
        end = row[end_col]

        if pd.notna(start) and pd.notna(end):
            timeline_rows.append(
                {
                    "Project": project_name,
                    "Phase": phase_name,
                    "Start": start,
                    "End": end,
                    "Company": company,
                    "Lead Developer": lead,
                    "Assistant": assistant,
                }
            )

timeline_df = pd.DataFrame(timeline_rows)

st.subheader("Debug: Timeline Table")
st.write("Timeline rows:", len(timeline_df))
if not timeline_df.empty:
    st.dataframe(timeline_df.head(20))
else:
    st.info("Timeline table is empty. This usually means the phase date columns are missing or did not parse.")

# ----------------------------
# Visualization
# ----------------------------

st.header("Project Timeline")

if not timeline_df.empty:
    fig = px.timeline(
        timeline_df,
        x_start="Start",
        x_end="End",
        y="Project",
        color="Phase",
        hover_data=["Company", "Lead Developer", "Assistant"],
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No timeline data available.")

# ----------------------------
# Raw Data
# ----------------------------

with st.expander("Project Data Preview"):
    st.dataframe(filtered_projects.head(50))

with st.expander("People Data Preview"):
    st.dataframe(people.head(50))
