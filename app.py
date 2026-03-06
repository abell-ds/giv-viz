import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Development Dashboard", layout="wide")

st.title("Development Pipeline Dashboard")

projects = pd.read_csv("PROJECTS.csv")
people = pd.read_csv("PEOPLE.csv")

st.subheader("Raw Data")
with st.expander("Projects"):
    st.dataframe(projects)

with st.expander("People"):
    st.dataframe(people)

timeline_rows = []

phase_columns = [
    ("Precon / Architectural", "Precon/Architectural Start", "Precon/Architectural End"),
    ("LIHTC App", "LIHTC App Start", "LIHTC App End"),
    ("4% App", "4% App Start", "4% App End"),
    ("Zoning", "Zoning Start", "Zoning End"),
    ("Permitting", "Permitting Start", "Permitting End"),
    ("Sales", "Sales Start", "Sales End"),
    ("Construction", "Construction Start", "Construction End"),
    ("Conversion / Stabilization / 8609", "Conversion/Stabilization/8609 Start", "Conversion/Stabilization/8609 End"),
]

for _, row in projects.iterrows():
    for phase_name, start_col, end_col in phase_columns:
        start = row.get(start_col)
        end = row.get(end_col)

        if pd.notna(start) and pd.notna(end):
            timeline_rows.append({
                "Project Name": row["Project Name"],
                "Company": row["Company"],
                "Phase": phase_name,
                "Start": pd.to_datetime(start),
                "End": pd.to_datetime(end),
                "Lead Developer": row.get("Lead Developer"),
                "Asst Developer": row.get("Asst Developer"),
            })

timeline_df = pd.DataFrame(timeline_rows)

st.subheader("Project Timeline")

if not timeline_df.empty:
    fig = px.timeline(
        timeline_df,
        x_start="Start",
        x_end="End",
        y="Project Name",
        color="Phase",
        hover_data=["Company", "Lead Developer", "Asst Developer"],
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No valid phase date ranges found.")
