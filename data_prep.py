import re
from pathlib import Path

import pandas as pd


PHASE_PAIRS = [
    ("Precon/Architectural Start", "Precon/Architectural End", "Precon/Architectural"),
    ("LIHTC App Start", "LIHTC App End", "LIHTC App"),
    ("4% App Start", "4% App End", "4% App"),
    ("Zoning Start", "Zoning End", "Zoning"),
    ("Permitting Start", "Permitting End", "Permitting"),
    ("Sales Start", "Sales End", "Sales"),
    ("Construction Start", "Construction End", "Construction"),
    (
        "Conversion/Stabilization/8609 Start",
        "Conversion/Stabilization/8609 End",
        "Conversion/Stabilization/8609",
    ),
]

NAME_MAP = {
    "Abbie": "Abbie Simons",
    "Amanda": "Amanda Dillon",
    "CJ": "CJ Hellige",
    "Jessica": "Jessica Long",
    "Kris": "Kris Long",
    "Melissa": "Melissa Jensen",
    "Morgan": "Morgan Julian",
    "Roberta": "Roberta Reichgelt",
    "Russell": "Russell Opatz",
    "Sam": "Sam Wiesenberg",
}

PEOPLE_DATE_COLS = ["Start Date", "5 yr", "10 yr", "15 yr"]


def clean_name(value):
    if pd.isna(value):
        return None
    value = str(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"[\u200B-\u200D\uFEFF]", "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip()
    return value if value else None


def map_name(value):
    cleaned = clean_name(value)
    return NAME_MAP.get(cleaned, cleaned)


def to_quarter_period(value):
    if pd.isna(value):
        return None

    if isinstance(value, pd.Period):
        return value.asfreq("Q")

    if isinstance(value, pd.Timestamp):
        return pd.Period(value, freq="Q")

    value = clean_name(value)
    if value is None:
        return None

    # Handles strings like "Q4 2026"
    if value.upper().startswith("Q") and " " in value:
        parts = value.upper().split()
        if len(parts) == 2:
            q, year = parts
            q_num = q.replace("Q", "")
            if q_num in {"1", "2", "3", "4"} and year.isdigit():
                return pd.Period(f"{year}Q{q_num}", freq="Q")

    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return None

    return pd.Period(dt, freq="Q")


def quarter_range(start, end):
    start_q = to_quarter_period(start)
    end_q = to_quarter_period(end)

    if start_q is None or end_q is None:
        return []

    return list(pd.period_range(start_q, end_q, freq="Q"))


def load_source_data(
    people_path: str | Path = "PEOPLE.csv",
    projects_path: str | Path = "PROJECTS.csv",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    people_df = pd.read_csv(people_path)
    projects_df = pd.read_csv(projects_path)
    return people_df, projects_df


def clean_people_df(people_df: pd.DataFrame) -> pd.DataFrame:
    people_df = people_df.copy()

    people_df["Name_clean"] = people_df["Name"].apply(clean_name)

    for col in PEOPLE_DATE_COLS:
        if col in people_df.columns:
            people_df[col] = pd.to_datetime(people_df[col], errors="coerce")

    people_df["Role"] = people_df["Role"].apply(clean_name)
    people_df["Company"] = people_df["Company"].apply(clean_name)
    people_df["Salary"] = pd.to_numeric(people_df["Salary"], errors="coerce")

    return people_df


def clean_projects_df(projects_df: pd.DataFrame) -> pd.DataFrame:
    projects_df = projects_df.copy()

    projects_df.columns = [str(c).strip() for c in projects_df.columns]

    projects_df["Project Name"] = projects_df["Project Name"].apply(clean_name)
    projects_df["Company"] = projects_df["Company"].apply(clean_name)
    projects_df["Lead Developer"] = projects_df["Lead Developer"].apply(map_name)
    projects_df["Asst Developer"] = projects_df["Asst Developer"].apply(map_name)

    revenue_cols = [
        "Est Dev Fee (to company)",
        "Est Quarterly Dist (to company)",
        "Sale Proceeds",
    ]
    for col in revenue_cols:
        if col in projects_df.columns:
            projects_df[col] = pd.to_numeric(projects_df[col], errors="coerce")

    return projects_df


def build_gantt_df(projects_df: pd.DataFrame) -> pd.DataFrame:
    records = []

    for _, row in projects_df.iterrows():
        for start_col, end_col, phase_name in PHASE_PAIRS:
            start_val = row.get(start_col)
            end_val = row.get(end_col)

            start_ok = pd.notna(start_val) and clean_name(start_val) is not None
            end_ok = pd.notna(end_val) and clean_name(end_val) is not None

            if start_ok and end_ok:
                records.append(
                    {
                        "Project Name": row["Project Name"],
                        "Company": row.get("Company"),
                        "Lead Developer": row.get("Lead Developer"),
                        "Asst Developer": row.get("Asst Developer"),
                        "Phase": phase_name,
                        "Start": start_val,
                        "End": end_val,
                    }
                )

    return pd.DataFrame(records)


def build_person_quarter_df(gantt_df: pd.DataFrame) -> pd.DataFrame:
    records = []

    for _, row in gantt_df.iterrows():
        assigned_people = {
            person
            for person in [row.get("Lead Developer"), row.get("Asst Developer")]
            if person is not None
        }

        qtrs = quarter_range(row["Start"], row["End"])

        for person in assigned_people:
            for q in qtrs:
                records.append(
                    {
                        "Person": person,
                        "Project Name": row["Project Name"],
                        "Quarter": q,
                    }
                )

    return pd.DataFrame(records)


def build_workload(person_quarter_df: pd.DataFrame) -> pd.DataFrame:
    if person_quarter_df.empty:
        return pd.DataFrame()

    workload = (
        person_quarter_df.groupby(["Person", "Quarter"])["Project Name"]
        .nunique()
        .unstack(fill_value=0)
        .sort_index(axis=1)
    )

    person_order = (
        person_quarter_df.groupby("Person")["Quarter"]
        .min()
        .sort_values()
        .index
    )

    return workload.reindex(person_order)


def build_workload_people(
    people_df: pd.DataFrame,
    workload: pd.DataFrame,
) -> pd.DataFrame:
    workload_people = people_df.merge(
        workload,
        left_on="Name_clean",
        right_index=True,
        how="left",
    )

    quarter_cols = [c for c in workload_people.columns if isinstance(c, pd.Period)]
    if quarter_cols:
        workload_people[quarter_cols] = workload_people[quarter_cols].fillna(0)

    workload_people = workload_people.drop(columns=["Name_clean"]).set_index("Name")
    return workload_people


def prepare_data(
    people_path: str | Path = "PEOPLE.csv",
    projects_path: str | Path = "PROJECTS.csv",
    verbose: bool = True,
) -> dict[str, pd.DataFrame]:
    people_raw, projects_raw = load_source_data(people_path, projects_path)

    people_df = clean_people_df(people_raw)
    projects_df = clean_projects_df(projects_raw)
    gantt_df = build_gantt_df(projects_df)
    person_quarter_df = build_person_quarter_df(gantt_df)
    workload = build_workload(person_quarter_df)
    workload_people = build_workload_people(people_df, workload)

    if verbose:
        quarter_cols = [c for c in workload_people.columns if isinstance(c, pd.Period)]
        print("people_df shape:", people_df.shape)
        print("projects_df shape:", projects_df.shape)
        print("gantt_df shape:", gantt_df.shape)
        print("person_quarter_df shape:", person_quarter_df.shape)
        print("workload shape:", workload.shape)
        print("workload_people shape:", workload_people.shape)
        print("quarter columns:", quarter_cols)

        if quarter_cols:
            zero_workload = workload_people.loc[
                workload_people[quarter_cols].sum(axis=1) == 0
            ].index.tolist()
            print("People with zero assigned workload:", zero_workload)
        else:
            print("No quarter columns created.")

    return {
        "people_df": people_df,
        "projects_df": projects_df,
        "gantt_df": gantt_df,
        "person_quarter_df": person_quarter_df,
        "workload": workload,
        "workload_people": workload_people,
    }
