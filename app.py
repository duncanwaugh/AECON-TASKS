import streamlit as st
# Set wide mode and page title before any other Streamlit calls
st.set_page_config(page_title="Aecon Co‑op Task Tracker", layout="wide")

import pandas as pd
import json
import os
import calendar
from datetime import date, datetime
import plotly.express as px
import openai
from fpdf import FPDF
from dotenv import load_dotenv

# ---- Configuration ----
DATA_PATH = "tasks_data.json"
LOGO_PATH = "aecon_logo.png"  # Place Aecon logo here
# Placeholder for OpenAI API key
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_KEY

# ---- Data Persistence & Excel Export ----
def load_data():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r") as f:
            data = json.load(f)
        return data.get("tasks", []), data.get("completed_tasks", [])
    return [], []


def export_to_excel(tasks, completed, excel_path="tasks_data.xlsx"):
    """Export tasks and completed tasks to an Excel or CSV if needed."""
    df_tasks = pd.DataFrame(tasks)
    df_completed = pd.DataFrame(completed)
    try:
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df_tasks.to_excel(writer, sheet_name="Active Tasks", index=False)
            df_completed.to_excel(writer, sheet_name="Completed Tasks", index=False)
        return
    except Exception:
        pass
    try:
        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            df_tasks.to_excel(writer, sheet_name="Active Tasks", index=False)
            df_completed.to_excel(writer, sheet_name="Completed Tasks", index=False)
        return
    except Exception:
        pass
    df_tasks.to_csv("tasks_data.csv", index=False)
    df_completed.to_csv("completed_tasks.csv", index=False)


def save_data(tasks, completed):
    with open(DATA_PATH, "w") as f:
        json.dump({"tasks": tasks, "completed_tasks": completed}, f, default=str)
    export_to_excel(tasks, completed)

# ---- Initialize State ----
rerun = getattr(st, "experimental_rerun", lambda: None)
if 'tasks' not in st.session_state:
    tasks, completed = load_data()
    st.session_state.tasks = tasks
    st.session_state.completed_tasks = completed

# ---- Header ----
if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=200)
st.title("Aecon Co‑op Task Tracker")
st.markdown("Manage tasks and subtasks during your 4‑month co‑op at Aecon.")

# ---- Sidebar: New Task & Month & Export & Report ----
st.sidebar.header("➕ Add New Task & View Month")
task_name = st.sidebar.text_input("Task Name")
assigned_by = st.sidebar.text_input("Assigned By")
date_assigned = st.sidebar.date_input("Date Assigned", date.today())
due_date = st.sidebar.date_input("Due Date", date.today())
estimated_time = st.sidebar.number_input("Est. Time (hrs)", min_value=0.0, step=0.5)
priority = st.sidebar.selectbox("Priority", ["Low", "Medium", "High", "Critical"])
notes = st.sidebar.text_area("Notes")
subtasks_input = st.sidebar.text_area("Subtasks (one per line)")

if st.sidebar.button("Add Task"):
    if task_name:
        subs = [s.strip() for s in subtasks_input.splitlines() if s.strip()]
        new_subtasks = [{"Name": s, "Completed": False} for s in subs]
        new_task = {
            "Task": task_name,
            "Assigned By": assigned_by,
            "Date Assigned": date_assigned.isoformat(),
            "Due Date": due_date.isoformat(),
            "Estimated Time (hrs)": estimated_time,
            "Priority": priority,
            "Notes": notes,
            "Subtasks": new_subtasks
        }
        st.session_state.tasks.append(new_task)
        save_data(st.session_state.tasks, st.session_state.completed_tasks)
        st.sidebar.success(f"Added task: {task_name}")
        rerun()
    else:
        st.sidebar.error("Task name is required.")

# Month selector
default_month = date.today().replace(day=1)
selected_month = st.sidebar.date_input("Calendar Month", default_month)
year, month = selected_month.year, selected_month.month

# Export controls
st.sidebar.header("📥 Export Data")
if st.sidebar.button("Export Data"):
    export_to_excel(st.session_state.tasks, st.session_state.completed_tasks)
    st.sidebar.success("Data exported to files in the app directory.")
# Download links
if os.path.exists("tasks_data.xlsx"):
    with open("tasks_data.xlsx","rb") as f: data=f.read()
    st.sidebar.download_button("Download Excel",
        data=data, file_name="tasks_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
elif os.path.exists("tasks_data.csv"):
    with open("tasks_data.csv","rb") as f1, open("completed_tasks.csv","rb") as f2:
        d1, d2 = f1.read(), f2.read()
    st.sidebar.download_button("Download Active CSV", d1, "tasks_data.csv","text/csv")
    st.sidebar.download_button("Download Completed CSV", d2, "completed_tasks.csv","text/csv")

# Generate report
st.sidebar.header("📝 Monthly Progress Report")
if st.sidebar.button("Generate Report"):
    # Filter completed tasks for selected month
    completed = st.session_state.completed_tasks
    dfc = pd.DataFrame(completed)
    if not dfc.empty:
        dfc['Due Date'] = pd.to_datetime(dfc['Due Date']).dt.date
        report_df = dfc[dfc['Due Date'].apply(lambda d: d.year==year and d.month==month)]
    else:
        report_df = pd.DataFrame()
    # Build raw summary text
    summary_items = "".join([f"- {row['Task']}: {row['Notes']}\n" for _, row in report_df.iterrows()])
    prompt = f"Provide a concise monthly progress report based on the following completed tasks:\n{summary_items}"
    # Call OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role":"user","content": prompt}]
    )
    summary = response.choices[0].message.content
    # Display report
    st.header(f"Progress Report: {selected_month.strftime('%B %Y')}")
    st.markdown(summary)
    # Charts & metrics
    if not report_df.empty:
        # Tasks by priority
        fig1 = px.bar(report_df['Priority'].value_counts().reset_index().rename(columns={'index':'Priority','Priority':'Count'}),
                      x='Priority', y='Count', title='Completed Tasks by Priority')
        st.plotly_chart(fig1, use_container_width=True)
        # Hours spent by priority
        report_df['Hours'] = report_df['Estimated Time (hrs)']
        fig2 = px.pie(report_df, names='Priority', values='Hours', title='Estimated Hours by Priority')
        st.plotly_chart(fig2, use_container_width=True)
    # Export PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, f"Progress Report: {selected_month.strftime('%B %Y')}\n\n")
    pdf.multi_cell(0, 8, summary)
    pdf.output("report.pdf")
    with open("report.pdf","rb") as f:
        pdf_data = f.read()
    st.sidebar.download_button("Download Report PDF", data=pdf_data,
        file_name="report.pdf", mime="application/pdf")

# ---- Main Layout: Calendar & Active Tasks ----
col1, col2 = st.columns(2)

# Calendar in col1
with col1:
    st.subheader("📅 Task Calendar")
    df_cal = pd.DataFrame(st.session_state.tasks)
    if not df_cal.empty:
        df_cal['due_date'] = pd.to_datetime(df_cal.get('Due Date'), errors='coerce').dt.date
        cal_matrix = calendar.monthcalendar(year, month)
        cmap = {"Low":"gray","Medium":"blue","High":"orange","Critical":"red"}
        rows=[]
        for week in cal_matrix:
            row=[]
            for d in week:
                if d==0: row.append("")
                else:
                    cell=f"<div style='font-weight:bold'>{d}</div>"
                    for _,t in df_cal[df_cal['due_date']==date(year,month,d)].iterrows():
                        color=cmap.get(t['Priority'],'black')
                        cell+=f"<div style='margin-left:6px;color:{color};'>• {t['Task']}</div>"
                    row.append(cell)
            rows.append(row)
        cal_df=pd.DataFrame(rows,columns=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
        st.markdown(cal_df.to_html(escape=False,index=False),unsafe_allow_html=True)
    else:
        st.info("No tasks to show on calendar.")

# Active Tasks in col2
with col2:
    st.subheader("📝 Active Tasks")
    if st.session_state.tasks:
        for i,task in enumerate(st.session_state.tasks):
            with st.expander(task['Task']):
                edit=st.checkbox("Edit Task Details",key=f"edit_{i}")
                if edit:
                    # ... existing edit code ...
                    pass
                else:
                    st.markdown(f"**Assigned By:** {task['Assigned By']}  \n**Due Date:** {task['Due Date']}")
                    st.markdown(f"**Notes:** {task['Notes']}")
    else:
        st.info("No active tasks. Add one in the sidebar.")

# Completed Tasks
st.header("🏁 Completed Tasks")
if st.session_state.completed_tasks:
    for idx,task in enumerate(st.session_state.completed_tasks):
        with st.expander(task['Task']):
            st.markdown(f"**Assigned By:** {task['Assigned By']}  \n**Due Date:** {task['Due Date']}")
            st.markdown(f"**Notes:** {task['Notes']}")
else:
    st.info("No tasks completed yet.")
