import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
from PIL import Image
import uuid
import shutil
import base64
import json   

# 1. PATH SETUP
# Use an absolute data folder next to this script so the DB persists across restarts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_FOLDER, exist_ok=True)
DB_PATH = os.path.join(DATA_FOLDER, "sunsys_erp.db")
ATTACHMENT_PATH = os.path.join(DATA_FOLDER, "attachments")
os.makedirs(ATTACHMENT_PATH, exist_ok=True)

# 2. UPDATED GET_DB
def get_db():
    return sqlite3.connect(DB_PATH)

# 3. DATABASE INITIALIZATION FUNCTION
def init_db():
    conn = get_db()
    c = conn.cursor()
    # Create Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 username TEXT PRIMARY KEY, 
                 password TEXT, 
                 full_name TEXT, 
                 dept TEXT, 
                 designation TEXT, 
                 phone TEXT, 
                 role TEXT)''')
    
    # Insert Default Admin if not exists
    c.execute("""INSERT OR IGNORE INTO users (username, password, full_name, dept, designation, phone, role) 
                 VALUES (?,?,?,?,?,?,?)""",
              ("admin", "admin2026", "HR Manager", "HR & Admin", "HR Head", "", "Admin"))
    
    # Create Tasks Table
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 description TEXT, assigned_to TEXT, dept TEXT,
                 status TEXT, priority TEXT, frequency TEXT,
                 due_date TEXT, due_time TEXT, admin_file TEXT, 
                 emp_remark TEXT, emp_screenshot TEXT, timestamp TEXT)''')
    
    conn.commit()
    conn.close()

# 4. CRITICAL: TRIGGER INITIALIZATION
# This must run before the login_page() call
init_db()
# ===================================================================


# Ensure attachments folder exists (do not delete files on restart)
os.makedirs(ATTACHMENT_PATH, exist_ok=True)


# ====================== DATABASE SETUP ======================
# Second init_db removed to prevent duplicate definitions

# ====================== HELPER FUNCTION TO MIGRATE DB ======================
def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Add due_time column if it doesn't exist
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN due_time TEXT")
    except:
        pass
    # Add columns for multiple file storage as JSON
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN admin_files_json TEXT DEFAULT '[]'")
    except:
        pass
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN emp_files_json TEXT DEFAULT '[]'")
    except:
        pass
    conn.commit()
    conn.close()

migrate_db()
    

# ====================== HELPER FUNCTION TO DISPLAY PDF (New Feature) ======================
def display_pdf(pdf_path):
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'''
            <iframe src="data:application/pdf;base64,{base64_pdf}" 
                    width="100%" height="600" 
                    type="application/pdf">
            </iframe>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.info("No PDF attached for this task.")

# ====================== ATTRACTIVE UI/UX STYLING ======================
st.set_page_config(page_title="SunSys ERP", page_icon="☀️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-size: 18px !important; }
    h1 { font-size: 48px !important; font-weight: 700; }
    h2 { font-size: 36px !important; }
    h3 { font-size: 28px !important; }
    
    .main-header { 
        background: linear-gradient(135deg, #1C4694 0%, #E47F15 100%); 
        padding: 30px; border-radius: 20px; color: white; 
        margin-bottom: 25px; box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    }
    
    .live-time { 
        font-size: 22px; font-weight: 700; color: #E47F15; 
        background: white; padding: 15px; border-radius: 15px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;
    }
    
    .card { 
        background: white; padding: 25px; border-radius: 18px; 
        box-shadow: 0 6px 20px rgba(0,0,0,0.1); margin-bottom: 20px;
    }
    
    .stButton>button { 
        height: 55px; font-weight: 700; border-radius: 14px; 
        background: linear-gradient(90deg, #1C4694, #E47F15); color: white;
        font-size: 18px;
    }
    
    .stDataFrame { font-size: 18px !important; }
    </style>
""", unsafe_allow_html=True)

# ====================== HEADER WITH LIVE TIME & DATE ======================
import streamlit.components.v1 as components

col1, col2, col3 = st.columns([1.2, 3.5, 2.2])

with col1:
    if os.path.exists("sunsys logo.png"):
        st.image("sunsys logo.png", width=200)
    else:
        st.title("☀️ SunSys")

with col2:
    st.markdown('<div class="main-header"><h1>SunSys ERP Portal</h1></div>', unsafe_allow_html=True)

with col3:
    components.html(
        """
        <div style="
            background: rgba(28, 70, 148, 0.05); 
            padding: 15px; 
            border-radius: 12px; 
            border-left: 5px solid #E47F15;
            font-family: 'Segoe UI', sans-serif;
            text-align: center;
        ">
            <div id="date" style="font-size: 14px; color: #666; font-weight: 600;"></div>
            <div id="clock" style="font-size: 28px; color: #1C4694; font-weight: 800; margin-top: 5px;"></div>
        </div>

        <script>
            function updateClock() {
                const now = new Date();
                const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
                document.getElementById('date').innerText = now.toLocaleDateString('en-US', dateOptions);
                const timeOptions = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
                document.getElementById('clock').innerText = now.toLocaleTimeString('en-US', timeOptions);
            }
            setInterval(updateClock, 1000);
            updateClock();
        </script>
        """,
        height=110,
    )

# ====================== AUTHENTICATION ======================
if "auth" not in st.session_state:
    st.session_state.update({"auth": False, "role": None, "user": None, "dept": None})

def login_page():
    st.markdown("<h2 style='text-align:center; color:#1C4694;'>🔐 Department Center Login</h2>", unsafe_allow_html=True)
    with st.container(border=True):
        role = st.radio("Select Access Type", ["Employee", "HR Admin"], horizontal=True)
        
        if role == "HR Admin":
            username = st.text_input("Admin Username")
            password = st.text_input("Password", type="password")
            if st.button("Enter HR Command Center", use_container_width=True):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    result = conn.execute("SELECT dept FROM users WHERE username=? AND password=? AND role='Admin'", 
                                        (username.strip(), password.strip())).fetchone()
                    if result:
                        st.session_state.update({"auth": True, "role": "Admin", "user": username})
                        st.rerun()
                    else:
                        st.error("❌ Invalid Admin Credentials")
                finally:
                    conn.close()
        
        else:
            username = st.text_input("Employee Username")
            password = st.text_input("Password", type="password")
            selected_dept = st.selectbox("Choose Your Department Center", 
                                       ["Solar Installation", "Technical Support", "Sales & Marketing", "HR & Admin", "Accounts"])
            
            if st.button("Enter My Department Center", use_container_width=True):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    # Strip whitespace from inputs for comparison
                    result = conn.execute("SELECT dept FROM users WHERE username=? AND password=? AND role='Employee'", 
                                        (username.strip(), password.strip())).fetchone()
                    if result:
                        stored_dept = result[0].strip() if result[0] else ""
                        selected_dept_clean = selected_dept.strip()
                        if stored_dept == selected_dept_clean:
                            st.session_state.update({"auth": True, "role": "Employee", "user": username, "dept": selected_dept})
                            st.rerun()
                        else:
                            st.error(f"❌ Department mismatch. Your registered department is '{stored_dept}' but you selected '{selected_dept_clean}'")
                    else:
                        st.error("❌ Invalid username or password")
                finally:
                    conn.close()

if not st.session_state.auth:
    login_page()
    st.stop()

if st.sidebar.button("🚪 Logout"):
    st.session_state.auth = False
    st.rerun()

# ====================== HELPER FUNCTION: GET RECENTLY UPDATED TASKS ======================
def get_recent_task_updates(hours=24):
    """Fetch tasks updated in the last N hours with employee details"""
    cutoff_time = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
    conn = get_db()
    recent_tasks = pd.read_sql("""
        SELECT 
            t.id,
            t.description,
            t.assigned_to,
            u.full_name,
            t.status,
            t.priority,
            t.emp_remark,
            t.timestamp as assigned_date,
            CASE WHEN t.emp_remark != '' AND t.emp_remark IS NOT NULL THEN datetime('now') ELSE NULL END as updated_time
        FROM tasks t
        LEFT JOIN users u ON t.assigned_to = u.username
        WHERE (t.emp_remark IS NOT NULL AND t.emp_remark != '')
           OR (t.status IN ('In Progress', 'Need Help', 'Work Completed'))
        ORDER BY t.id DESC
        LIMIT 20
    """, conn)
    conn.close()
    return recent_tasks

def get_status_badge_color(status):
    """Return color based on task status"""
    if status == "Work Completed":
        return "🟢 Completed"
    elif status == "In Progress":
        return "🟡 In Progress"
    elif status == "Need Help":
        return "🔴 Need Help"
    else:
        return "⚪ Pending"

# ====================== ADMIN PANEL ======================
if st.session_state.role == "Admin":
    st.header("📊 HR Command Center")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 Assign Task", "👥 Team Overview", "✏️ Edit/Delete", "📊 Dashboard", "➕ Add/Remove Employee", "🔔 Live Updates"])
    
    with tab1:
        st.subheader("Assign New Task")
        # Department selector outside form for dynamic updates
        dept_col, _ = st.columns([1, 3])
        with dept_col:
            selected_dept = st.selectbox("📍 Select Department", ["Solar Installation", "Technical Support", "Sales & Marketing", "HR & Admin", "Accounts"], key="admin_dept_select")
        
        # Fetch employees based on selected department
        emps_df = pd.read_sql("SELECT username, full_name FROM users WHERE role='Employee' AND dept=?", get_db(), params=(selected_dept,))
        employee_list = [f"{row['full_name']} ({row['username']})" for _, row in emps_df.iterrows()]
        
        if emps_df.empty:
            st.warning(f"📍 No employees found in **{selected_dept}**.")
        else:
            st.success(f"📍 Found **{len(emps_df)}** employee(s) in **{selected_dept}**")
            st.write(", ".join([row['full_name'] for _, row in emps_df.iterrows()]))
        
        with st.form("assign_task", clear_on_submit=True):
            desc = st.text_area("Task Description", height=140)
            c1, c2, c3, c4 = st.columns(4)
            
            # Department (hidden, using selected_dept from outside)
            dept = selected_dept
            
            if emps_df.empty:
                c2.write("No employees available for assignment.")
                assigned_to = None
            else:
                selected_emp = c2.selectbox("👤 Assign To", employee_list, key="form_emp_select")
                assigned_to = selected_emp.split("(")[-1].strip(")") if "(" in selected_emp else None
            
            priority = c3.selectbox("Priority", ["High", "Medium", "Low"])
            frequency = c4.selectbox("Frequency", ["Daily", "Weekly", "Fortnightly", "One-Time"])
            
            # --- NEW TIME & FILE OPTIONS ---
            col_date, col_time = st.columns(2)
            due_date = col_date.date_input("Due Date", datetime.now().date() + timedelta(days=7))
            due_time = col_time.time_input("Due Time (Deadline)", value=datetime.now().time())
            
            admin_file = st.file_uploader("📎 Attach Resources (PDF, Excel, Video, Image) - Upload Multiple Files", 
                                        type=["pdf", "xlsx", "xls", "mp4", "jpg", "png", "jpeg", "doc", "docx", "txt"],
                                        accept_multiple_files=True)
            
            if st.form_submit_button("🚀 Assign Task"):
                if not desc:
                    st.error("❌ Please enter a task description.")
                elif not assigned_to:
                    st.error("❌ Please select an employee from the selected department.")
                else:
                    try:
                        admin_files_json = "[]"
                        if admin_file:
                            os.makedirs(ATTACHMENT_PATH, exist_ok=True)
                            file_paths = []
                            for uploaded_file in admin_file:
                                file_ext = uploaded_file.name.split('.')[-1]
                                file_path = os.path.join(ATTACHMENT_PATH, f"admin_{uuid.uuid4().hex[:8]}.{file_ext}")
                                with open(file_path, "wb") as f:
                                    f.write(uploaded_file.getbuffer())
                                file_paths.append(file_path)
                            admin_files_json = json.dumps(file_paths)
                        
                        conn = get_db()
                        conn.execute("""INSERT INTO tasks 
                                     (description, assigned_to, dept, status, priority, frequency, due_date, due_time, admin_file, admin_files_json, timestamp)
                                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                                     (desc, assigned_to, dept, "Pending", priority, frequency, 
                                      due_date.strftime("%Y-%m-%d"), due_time.strftime("%H:%M"), 
                                      admin_files_json[:1] if admin_files_json != "[]" else "", 
                                      admin_files_json, 
                                      datetime.now().strftime("%Y-%m-%d %H:%M")))
                        conn.commit()
                        conn.close()
                        st.success("✅ Task Assigned Successfully!")
                        st.info(f"📎 {len(json.loads(admin_files_json))} file(s) attached")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error assigning task: {str(e)}")

    with tab2:
        st.subheader("👥 Team Member Directory")
        employees = pd.read_sql("SELECT username, full_name, dept, designation, phone FROM users WHERE role='Employee'", get_db())
        
        if employees.empty:
            st.info("No employees added yet.")
        else:
            selected_member = st.selectbox("Select Team Member to View Details", employees['full_name'].tolist())
            member = employees[employees['full_name'] == selected_member].iloc[0]
            
            st.markdown(f"""
                <div class="card">
                    <h3>{member['full_name']}</h3>
                    <p><strong>Department:</strong> {member['dept']}<br>
                       <strong>Designation:</strong> {member['designation']}<br>
                       <strong>Phone:</strong> {member['phone']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            if member['phone']:
                wa_link = f"https://wa.me/{member['phone']}?text=Hello%20{member['full_name']}%2C%20regarding%20your%20task..."
                st.markdown(f"[💬 Message on WhatsApp]({wa_link})")
            
            st.divider()
            st.subheader(f"Tasks & Proofs for {member['full_name']}")
            
            tasks_df = pd.read_sql(""" 
                SELECT id, description, status, priority, frequency, due_date, 
                       emp_remark, emp_screenshot, emp_files_json
                FROM tasks 
                WHERE assigned_to = ?
            """, get_db(), params=(member['username'],))
            
            if tasks_df.empty:
                st.info("No tasks assigned yet.")
            else:
                for _, row in tasks_df.iterrows():
                    with st.container(border=True):
                        # Status indicator with badge
                        col_title, col_badge = st.columns([3, 1])
                        with col_title:
                            st.write(f"**Task:** {row['description']}")
                        with col_badge:
                            st.markdown(f"### {get_status_badge_color(row['status'])}")
                        
                        col_main, col_priority = st.columns([3, 1])
                        with col_main:
                            st.caption(f"Frequency: **{row['frequency']}** | Due: **{row.get('due_date','N/A')}**")
                        with col_priority:
                            if row['priority'] == 'High':
                                st.error("🔴 HIGH PRIORITY")
                            elif row['priority'] == 'Medium':
                                st.warning("🟡 MEDIUM PRIORITY")
                            else:
                                st.info("🟢 LOW PRIORITY")
                        
                        if row.get('emp_remark'):
                            st.success(f"💬 **Employee Note:** _{row['emp_remark']}_")
                        
                        # Display multiple uploaded files
                        try:
                            emp_files_json = row.get('emp_files_json', '[]')
                            emp_files = json.loads(emp_files_json) if emp_files_json else []
                            
                            if emp_files:
                                st.subheader("📎 Uploaded Files")
                                for file_path in emp_files:
                                    if os.path.exists(file_path):
                                        file_name = os.path.basename(file_path)
                                        file_ext = file_name.split('.')[-1].lower()
                                        
                                        col1, col2 = st.columns([3, 1])
                                        with col1:
                                            st.write(f"📄 {file_name}")
                                        with col2:
                                            try:
                                                with open(file_path, "rb") as f:
                                                    st.download_button(
                                                        label="⬇️ Download",
                                                        data=f.read(),
                                                        file_name=file_name,
                                                        key=f"download_{row['id']}_{os.path.basename(file_path)}"
                                                    )
                                            except:
                                                st.write("Unable to download")
                            else:
                                st.info("No files uploaded yet.")
                        except Exception as e:
                            st.warning(f"Error loading files: {str(e)}")
                        
                        st.divider()

    with tab3:
        st.subheader("Edit / Delete Task")
        all_tasks = pd.read_sql("SELECT id, description FROM tasks ORDER BY id DESC", get_db())
        
        if all_tasks.empty:
            st.info("No tasks available.")
        else:
            task_options = [f"ID {row['id']}: {row['description'][:50]}..." for _, row in all_tasks.iterrows()]
            selected_task_option = st.selectbox("Select Task", task_options)
            task_id = int(selected_task_option.split(":")[0].replace("ID ", ""))
            
            task_data = pd.read_sql("SELECT * FROM tasks WHERE id=?", get_db(), params=(task_id,)).iloc[0]
            
            with st.form("edit_form"):
                new_desc = st.text_area("Task Description", value=task_data['description'], height=100)
                new_status = st.selectbox("Status", ["Pending", "In Progress", "Need Help", "Work Completed"], 
                                        index=["Pending","In Progress","Need Help","Work Completed"].index(task_data['status']))
                new_priority = st.selectbox("Priority", ["High", "Medium", "Low"], 
                                          index=["High","Medium","Low"].index(task_data['priority']))
                new_due = st.date_input("Due Date", value=datetime.strptime(task_data['due_date'], "%Y-%m-%d").date() if task_data['due_date'] else datetime.now().date())
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Update Task"):
                        conn = get_db()
                        conn.execute("""UPDATE tasks SET description=?, status=?, priority=?, due_date=? WHERE id=?""",
                                    (new_desc, new_status, new_priority, new_due.strftime("%Y-%m-%d"), task_id))
                        conn.commit()
                        conn.close()
                        st.success("Task updated successfully!")
                        st.rerun()
                
                with col2:
                    confirm = st.checkbox("⚠️ I confirm I want to delete this task")
                    if st.form_submit_button("🗑️ Delete Task", type="secondary", disabled=not confirm):
                        conn = get_db()
                        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
                        conn.commit()
                        conn.close()
                        st.success("Task deleted successfully!")
                        st.rerun()

    with tab4:
        st.subheader("📊 Overall Dashboard & Task Analytics")
        col1, col2, col3, col4 = st.columns(4)
        
        total_tasks = pd.read_sql("SELECT COUNT(*) as count FROM tasks", get_db()).iloc[0]['count']
        completed = pd.read_sql("SELECT COUNT(*) as count FROM tasks WHERE status='Work Completed'", get_db()).iloc[0]['count']
        pending = pd.read_sql("SELECT COUNT(*) as count FROM tasks WHERE status != 'Work Completed'", get_db()).iloc[0]['count']
        overdue = pd.read_sql(""" 
            SELECT COUNT(*) as count FROM tasks 
            WHERE due_date < ? AND status != 'Work Completed'
        """, get_db(), params=(datetime.now().date().strftime("%Y-%m-%d"),)).iloc[0]['count']
        
        with col1:
            st.metric("Total Tasks", total_tasks)
        with col2:
            st.metric("Completed", completed, delta=f"{completed} done")
        with col3:
            st.metric("Pending", pending)
        with col4:
            st.metric("Overdue", overdue, delta=f"{overdue} urgent", delta_color="inverse")
        
        st.divider()
        st.subheader("📋 All Tasks Overview")
        detailed_df = pd.read_sql(""" 
            SELECT 
                t.id,
                t.description as task_description,
                u.full_name as employee_name,
                t.dept as department,
                t.status,
                t.priority,
                t.frequency,
                t.due_date,
                t.timestamp as assigned_date,
                t.emp_remark as employee_remark
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.username
            ORDER BY t.id DESC
        """, get_db())
        
        if not detailed_df.empty:
            # Display tasks with visual indicators
            for idx, (_, row) in enumerate(detailed_df.iterrows()):
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**Task #{row['id']}:** {row['task_description'][:60]}...")
                        st.caption(f"👤 {row['employee_name']} | 🏢 {row['department']}")
                    
                    with col2:
                        st.markdown(f"### {get_status_badge_color(row['status'])}")
                    
                    with col3:
                        if row['priority'] == 'High':
                            st.error("🔴 HIGH")
                        elif row['priority'] == 'Medium':
                            st.warning("🟡 MEDIUM")
                        else:
                            st.info("🟢 LOW")
                    
                    col_info1, col_info2, col_info3 = st.columns(3)
                    with col_info1:
                        st.caption(f"📅 Due: {row['due_date']}")
                    with col_info2:
                        st.caption(f"🔄 Frequency: {row['frequency']}")
                    with col_info3:
                        st.caption(f"📌 Assigned: {row['assigned_date'][:10]}")
                    
                    if row['employee_remark']:
                        st.info(f"💬 **Employee Update:** {row['employee_remark']}")
        else:
            st.info("No tasks have been assigned yet.")
        
        st.divider()
        st.subheader("📍 Department-wise Task Summary")
        dept_summary = pd.read_sql(""" 
            SELECT 
                t.dept as department,
                COUNT(*) as total_tasks,
                SUM(CASE WHEN t.status = 'Work Completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN t.status != 'Work Completed' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN t.due_date < ? AND t.status != 'Work Completed' THEN 1 ELSE 0 END) as overdue
            FROM tasks t
            GROUP BY t.dept
        """, get_db(), params=(datetime.now().date().strftime("%Y-%m-%d"),))
        
        st.dataframe(dept_summary, use_container_width=True, hide_index=True)

    with tab5:
        col_add, col_rem = st.columns(2)
        
        with col_add:
            st.subheader("➕ Add New Employee")
            with st.form("add_new_employee", clear_on_submit=True):
                full_name = st.text_input("Full Name *")
                username = st.text_input("Username (Login ID) *")
                password = st.text_input("Password *", type="password")
                dept = st.selectbox("Department", 
                                  ["Solar Installation", "Technical Support", "Sales & Marketing", "HR & Admin", "Accounts"])
                designation = st.text_input("Designation")
                phone = st.text_input("Phone Number")
                
                if st.form_submit_button("✅ Add Employee", type="primary"):
                    if full_name and username and password and dept:
                        try:
                            conn = get_db()
                            # Strip whitespace from inputs to avoid login issues
                            conn.execute("""INSERT INTO users 
                                         (username, password, full_name, dept, designation, phone, role) 
                                         VALUES (?,?,?,?,?,?,?)""",
                                         (username.strip(), password.strip(), full_name.strip(), dept.strip(), designation.strip(), phone.strip(), "Employee"))
                            conn.commit()
                            conn.close()
                            st.success(f"✅ Employee **{full_name}** added!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Username '{username}' already exists or error: {str(e)}")
                    else:
                        st.error("Please fill all required fields (*)")

        with col_rem:
            st.subheader("🗑️ Remove Employee")
            emp_list_df = pd.read_sql("SELECT username, full_name, dept FROM users WHERE role='Employee'", get_db())
            
            if emp_list_df.empty:
                st.info("No employees found in database.")
            else:
                options = {f"{row['full_name']} ({row['username']}) - {row['dept']}": row['username'] 
                           for _, row in emp_list_df.iterrows()}
                
                selected_to_remove = st.selectbox("Select Employee to Remove", options.keys())
                target_user = options[selected_to_remove]
                
                confirm = st.checkbox(f"I confirm I want to delete {target_user}")
                
                if st.button("❌ Permanent Delete", type="secondary", use_container_width=True):
                    if confirm:
                        conn = get_db()
                        conn.execute("DELETE FROM users WHERE username=?", (target_user,))
                        conn.execute("DELETE FROM tasks WHERE assigned_to=?", (target_user,))
                        conn.commit()
                        conn.close()
                        st.warning(f"Employee {target_user} and their tasks have been removed.")
                        st.rerun()
                    else:
                        st.error("Please check the confirmation box first.")

    with tab6:
        st.subheader("🔔 Live Task Update Notifications")
        st.info("📬 Real-time updates when employees submit task progress")
        
        # Refresh button
        col_refresh, col_filter = st.columns([1, 3])
        with col_refresh:
            if st.button("🔄 Refresh Now", use_container_width=True, type="primary"):
                st.rerun()
        
        with col_filter:
            show_hours = st.slider("Show updates from last (hours)", 1, 168, 24)
        
        st.divider()
        
        # Get recent updates
        recent_updates = get_recent_task_updates(show_hours)
        
        if recent_updates.empty:
            st.info("✨ No task updates in the selected time period.")
        else:
            # Summary cards
            col1, col2, col3, col4 = st.columns(4)
            
            completed_count = len(recent_updates[recent_updates['status'] == 'Work Completed'])
            in_progress_count = len(recent_updates[recent_updates['status'] == 'In Progress'])
            need_help_count = len(recent_updates[recent_updates['status'] == 'Need Help'])
            
            with col1:
                st.metric("🟢 Completed", completed_count)
            with col2:
                st.metric("🟡 In Progress", in_progress_count)
            with col3:
                st.metric("🔴 Need Help", need_help_count)
            with col4:
                st.metric("📊 Total Updates", len(recent_updates))
            
            st.divider()
            st.subheader("📋 Recent Activity")
            
            # Display updates with visual indicators
            for idx, (_, row) in enumerate(recent_updates.iterrows()):
                with st.container(border=True):
                    col_status, col_priority = st.columns([2, 1])
                    
                    with col_status:
                        st.markdown(f"**{row['full_name']}** - {get_status_badge_color(row['status'])}")
                        st.caption(f"📌 Task ID: {row['id']} | Priority: {row['priority']}")
                        st.write(f"📝 {row['description'][:100]}..." if len(str(row['description'])) > 100 else f"📝 {row['description']}")
                    
                    with col_priority:
                        if row['priority'] == 'High':
                            st.error("🔴 HIGH")
                        elif row['priority'] == 'Medium':
                            st.warning("🟡 MEDIUM")
                        else:
                            st.info("🟢 LOW")
                    
                    if row['emp_remark']:
                        st.markdown(f"**Employee Note:** _{row['emp_remark']}_")
                    
                    # Action buttons
                    col_view, col_contact = st.columns(2)
                    with col_view:
                        if st.button(f"👁️ View Full Details", key=f"view_{row['id']}", use_container_width=True):
                            st.session_state.expand_task = row['id']
                            st.rerun()
                    with col_contact:
                        if row['id'] and not pd.isna(row['id']):
                            st.info(f"✅ Last update received")

    st.divider()
    st.caption("© 2026 SunSys ERP Portal by Aditya kumar | All rights reserved.")

# ====================== EMPLOYEE PANEL ======================
elif st.session_state.role == "Employee":
    st.header(f"🚀 {st.session_state.dept} Center • Welcome, {st.session_state.user}")
    
    # Create tabs for Tasks and Security
    tab_tasks, tab_security = st.tabs(["📋 My Tasks", "🔐 Security & Password"])

    with tab_tasks:
        conn = get_db()
        tasks = pd.read_sql("SELECT * FROM tasks WHERE assigned_to = ?", conn, params=(st.session_state.user,))
        conn.close()
        
        if tasks.empty:
            st.info("No tasks assigned to you yet.")
        else:
            for _, row in tasks.iterrows():
                with st.container(border=True):
                    st.subheader(f"Task: {row['description']}")
                    st.warning(f"⏰ **Deadline:** {row['due_date']} at {row.get('due_time', 'Not set')}")
                    
                    # Resources Section - Display multiple admin files
                    try:
                        admin_files_json = row.get('admin_files_json', '[]')
                        admin_files = json.loads(admin_files_json) if admin_files_json else []
                        
                        if admin_files:
                            st.subheader("📦 Resources from Admin")
                            for file_path in admin_files:
                                if os.path.exists(file_path):
                                    file_name = os.path.basename(file_path)
                                    file_ext = file_name.split('.')[-1].lower()
                                    
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.write(f"📄 {file_name}")
                                    with col2:
                                        try:
                                            with open(file_path, "rb") as f:
                                                st.download_button(
                                                    label="⬇️",
                                                    data=f.read(),
                                                    file_name=file_name,
                                                    key=f"admin_dl_{row['id']}_{os.path.basename(file_path)}"
                                                )
                                        except:
                                            st.write("❌")
                    except Exception as e:
                        st.warning(f"Error loading resources: {str(e)}")
                    
                    st.divider()
                    
                    col_status, col_upload = st.columns(2)
                    with col_status:
                        new_status = st.selectbox("Update Status", ["Pending", "In Progress", "Work Completed"], key=f"s_{row['id']}")
                        remark = st.text_area("Notes", value=row.get('emp_remark', ''), key=f"r_{row['id']}")
                    with col_upload:
                        proof_file = st.file_uploader("📎 Upload Proof/Attachments - Multiple Files", 
                                                     type=["pdf", "xlsx", "xls", "mp4", "jpg", "png", "jpeg", "doc", "docx", "txt"],
                                                     key=f"p_{row['id']}", accept_multiple_files=True)

                    if st.button("🚀 Submit Update", key=f"b_{row['id']}", type="primary"):
                        try:
                            # Logic to save multiple files and update DB
                            emp_files_json = row.get('emp_files_json', '[]')
                            if emp_files_json == '[]' or not emp_files_json:
                                emp_files_json = '[]'
                            
                            current_files = json.loads(emp_files_json) if emp_files_json else []
                            
                            if proof_file:
                                os.makedirs(ATTACHMENT_PATH, exist_ok=True)
                                for uploaded_file in proof_file:
                                    file_ext = uploaded_file.name.split('.')[-1]
                                    file_path = os.path.join(ATTACHMENT_PATH, f"proof_{row['id']}_{uuid.uuid4().hex[:5]}.{file_ext}")
                                    with open(file_path, "wb") as f:
                                        f.write(uploaded_file.getbuffer())
                                    current_files.append(file_path)
                            
                            final_files_json = json.dumps(current_files)
                            
                            conn = get_db()
                            conn.execute("UPDATE tasks SET status=?, emp_remark=?, emp_screenshot=?, emp_files_json=? WHERE id=?", 
                                         (new_status, remark, final_files_json[:1] if final_files_json != "[]" else "", 
                                          final_files_json, row['id']))
                            conn.commit()
                            conn.close()
                            
                            st.success("✅ Work updated successfully!")
                            st.info(f"✔️ Status: {new_status} | {len(current_files)} file(s) uploaded | Saved at {datetime.now().strftime('%H:%M:%S')}")
                            st.balloons()
                            import time
                            time.sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error updating task: {str(e)}")

    with tab_security:
        st.subheader("Update Your Password")
        st.info("Keep your account secure by choosing a strong password.")
        
        with st.form("change_password_form"):
            current_pass = st.text_input("Current Password", type="password")
            new_pass = st.text_input("New Password", type="password")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("Update Password"):
                conn = get_db()
                # Verify current password
                user_data = conn.execute("SELECT password FROM users WHERE username=?", 
                                        (st.session_state.user.strip(),)).fetchone()
                
                if not current_pass or not new_pass:
                    st.error("Please fill all fields.")
                elif user_data[0] != current_pass:
                    st.error("❌ Current password is incorrect.")
                elif new_pass != confirm_pass:
                    st.error("❌ New passwords do not match.")
                elif len(new_pass) < 6:
                    st.warning("⚠️ New password should be at least 6 characters long.")
                else:
                    conn.execute("UPDATE users SET password=? WHERE username=?", 
                                 (new_pass, st.session_state.user))
                    conn.commit()
                    st.success("✅ Password updated successfully! Please login again next time.")
                conn.close()

    st.divider()
    st.caption("© 2026 SunSys ERP Portal by Aditya kumar | All rights reserved.")
