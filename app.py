import streamlit as st
# Set wide mode and page title before any other Streamlit calls
st.set_page_config(page_title="Aecon Co‑op Task Tracker", layout="wide")

import pandas as pd
import json
import os
import calendar
from datetime import date, datetime

# ---- Configuration ----
DATA_PATH = "tasks_data.json"
LOGO_PATH = "aecon_logo.png"  # Place Aecon logo here

# ---- Data Persistence ----
import pandas as pd  # for Excel export

def load_data():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r") as f:
            data = json.load(f)
        return data.get("tasks", []), data.get("completed_tasks", [])
    return [], []


def export_to_excel(tasks, completed, excel_path="tasks_data.xlsx"):
    """Export tasks and completed tasks to an Excel workbook with two sheets."""
    df_tasks = pd.DataFrame(tasks)
    df_completed = pd.DataFrame(completed)
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_tasks.to_excel(writer, sheet_name="Active Tasks", index=False)
        df_completed.to_excel(writer, sheet_name="Completed Tasks", index=False)


def save_data(tasks, completed):
    # Save JSON
    with open(DATA_PATH, "w") as f:
        json.dump({"tasks": tasks, "completed_tasks": completed}, f, default=str)
    # Also export to Excel
    try:
        export_to_excel(tasks, completed)
    except Exception as e:
        st.error(f"Failed to export to Excel: {e}")

# ---- Initialize State ----
# Rerun helper: alias Streamlit's experimental_rerun if available
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

# ---- Sidebar: New Task & Month ----
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

# ---- Main Layout: Calendar & Active Tasks Side-by-Side ----
col1, col2 = st.columns(2)

# Calendar in left column
with col1:
    st.subheader("📅 Task Calendar")
    df_cal = pd.DataFrame(st.session_state.tasks)
    if not df_cal.empty:
        df_cal['due_date'] = pd.to_datetime(
            df_cal.get('Due Date', df_cal.get('due_date', None)),
            errors='coerce'
        ).dt.date
        cal_matrix = calendar.monthcalendar(year, month)
        cmap = {"Low":"gray","Medium":"blue","High":"orange","Critical":"red"}
        html_rows = []
        for week in cal_matrix:
            cells = []
            for d in week:
                if d == 0:
                    cells.append("")
                else:
                    cell_html = f"<div style='font-weight:bold; text-align:left;'>{d}</div>"
                    for _, t in df_cal[df_cal['due_date'] == date(year, month, d)].iterrows():
                        color = cmap.get(t['Priority'], 'black')
                        task_name_html = t['Task']
                        cell_html += f"<div style='margin-left:6px; font-size:0.8em; color:{color};'>• {task_name_html}</div>"
                    cells.append(cell_html)
            html_rows.append(cells)
        cal_df = pd.DataFrame(html_rows, columns=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
        st.markdown(cal_df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("No tasks to show on calendar.")

# Active tasks in right column
with col2:
    st.subheader("📝 Active Tasks")
    if st.session_state.tasks:
        for i, task in enumerate(st.session_state.tasks):
            with st.expander(task['Task']):
                edit = st.checkbox("Edit Task Details", key=f"edit_{i}")
                if edit:
                    tn = st.text_input("Task Name", value=task['Task'], key=f"tn_{i}")
                    ab = st.text_input("Assigned By", value=task['Assigned By'], key=f"ab_{i}")
                    da = st.date_input("Date Assigned", datetime.fromisoformat(task['Date Assigned']).date(), key=f"da_{i}")
                    dd = st.date_input("Due Date", datetime.fromisoformat(task['Due Date']).date(), key=f"dd_{i}")
                    et = st.number_input("Est. Time (hrs)", value=task['Estimated Time (hrs)'], key=f"et_{i}")
                    pr = st.selectbox("Priority", ["Low","Medium","High","Critical"], index=["Low","Medium","High","Critical"].index(task['Priority']), key=f"pr_{i}")
                    no = st.text_area("Notes", value=task['Notes'], key=f"no_{i}")
                    # Add subtasks only in edit mode
                    new_sub = st.text_input("New Subtask", key=f"new_sub_{i}")
                    if st.button("Add Subtask", key=f"add_sub_{i}") and new_sub:
                        task['Subtasks'].append({"Name": new_sub, "Completed": False})
                        save_data(st.session_state.tasks, st.session_state.completed_tasks)
                        rerun()
                    if st.button("Save Changes", key=f"save_{i}"):
                        task.update({
                            'Task': tn, 'Assigned By': ab,
                            'Date Assigned': da.isoformat(), 'Due Date': dd.isoformat(),
                            'Estimated Time (hrs)': et, 'Priority': pr, 'Notes': no
                        })
                        save_data(st.session_state.tasks, st.session_state.completed_tasks)
                        st.success("Task updated.")
                        rerun()
                else:
                    st.markdown(f"**Assigned By:** {task['Assigned By']}  \n**Date Assigned:** {task['Date Assigned']}  \n**Due Date:** {task['Due Date']}  \n**Priority:** {task['Priority']}")
                    st.markdown(f"**Notes:** {task['Notes']}")
                    # List subtasks without progress bars
                    for j, s in enumerate(task.get('Subtasks', [])):
                        ck = st.checkbox(s['Name'], value=s.get('Completed', False), key=f"sub_{i}_{j}")
                        if ck != s['Completed']:
                            s['Completed'] = ck
                            save_data(st.session_state.tasks, st.session_state.completed_tasks)
                if st.button("Mark Task Completed", key=f"comp_{i}"):
                    st.session_state.completed_tasks.append(st.session_state.tasks.pop(i))
                    save_data(st.session_state.tasks, st.session_state.completed_tasks)
                    st.success(f"Completed: {task['Task']}")
                    rerun()
    else:
        st.info("No active tasks. Add one in the sidebar.")

# ---- Completed Tasks Below ----
st.header("🏁 Completed Tasks")
if st.session_state.completed_tasks:
    for idx, task in enumerate(st.session_state.completed_tasks):
        with st.expander(task['Task']):
            st.markdown(f"**Assigned By:** {task['Assigned By']}  \n**Date Assigned:** {task['Date Assigned']}  \n**Due Date:** {task['Due Date']}  \n**Priority:** {task['Priority']}")
            st.markdown(f"**Notes:** {task['Notes']}")
            if st.button("Delete Completed Task", key=f"del_comp_{idx}"):
                st.session_state.completed_tasks.pop(idx)
                save_data(st.session_state.tasks, st.session_state.completed_tasks)
                rerun()
else:
    st.info("No tasks completed yet.")

# ---- Sidebar Usage ----
st.sidebar.markdown(
    "---\n**Usage:**  \n"
    "- Add tasks/subtasks & pick month.  \n"
    "- View calendar and active tasks side-by-side.  \n"
    "- Completed tasks appear below with notes.  \n\n"
    "**Teams Calendar:**  \n"
    "Sync via Microsoft Graph API & Azure AD integration."
)
