import sqlite3
import os
import json
import hashlib
import secrets
from datetime import datetime
from pathlib import Path

DATA_FOLDER = Path("data")
DB_PATH = DATA_FOLDER / "sunsys_erp.db"
ATTACHMENT_PATH = DATA_FOLDER / "attachments"

DATA_FOLDER.mkdir(exist_ok=True)
ATTACHMENT_PATH.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _is_hashed_password(value: str) -> bool:
    return isinstance(value, str) and value.startswith("pbkdf2_sha256$") and value.count("$") == 3


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 120000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(stored_value: str, raw_password: str) -> bool:
    if not stored_value or not raw_password:
        return False
    if _is_hashed_password(stored_value):
        _, iterations, salt, hash_hex = stored_value.split("$", 3)
        new_hash = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt.encode("utf-8"), int(iterations)).hex()
        return secrets.compare_digest(new_hash, hash_hex)
    return stored_value == raw_password


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def table_has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def migrate_task_columns(conn: sqlite3.Connection):
    columns = {
        "due_time": "TEXT",
        "admin_files_json": "TEXT DEFAULT '[]'",
        "emp_files_json": "TEXT DEFAULT '[]'",
        "admin_file": "TEXT",
        "emp_screenshot": "TEXT"
    }
    for column_name, definition in columns.items():
        if not table_has_column(conn, "tasks", column_name):
            try:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {column_name} {definition}")
            except sqlite3.OperationalError:
                pass
    conn.commit()


def migrate_attachments_from_json(conn: sqlite3.Connection):
    if not table_has_column(conn, "tasks", "admin_files_json"):
        return
    tasks = conn.execute("SELECT id, admin_files_json, emp_files_json FROM tasks").fetchall()
    for task in tasks:
        for attachment_type, field_name, uploader in [
            ("admin", "admin_files_json", "admin"),
            ("employee", "emp_files_json", "employee"),
        ]:
            raw_value = task[field_name]
            if not raw_value:
                continue
            try:
                values = json.loads(raw_value)
            except Exception:
                continue
            if not isinstance(values, list):
                continue
            for path in values:
                if isinstance(path, str) and os.path.exists(path):
                    conn.execute(
                        "INSERT INTO attachments (task_id, uploaded_by, attachment_type, file_name, file_path, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (task["id"], uploader, attachment_type, os.path.basename(path), path, now_str()),
                    )
    conn.commit()


def ensure_default_admin(conn: sqlite3.Connection):
    cursor = conn.execute("SELECT password FROM users WHERE username = ?", ("admin",))
    row = cursor.fetchone()
    if row:
        password = row["password"]
        if not _is_hashed_password(password):
            conn.execute("UPDATE users SET password = ? WHERE username = ?", (hash_password(password), "admin"))
            conn.commit()
    else:
        conn.execute(
            "INSERT INTO users (username, password, full_name, dept, designation, phone, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("admin", hash_password("admin2026"), "HR Manager", "HR & Admin", "HR Head", "", "Admin", now_str()),
        )
        conn.commit()


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            dept TEXT,
            designation TEXT,
            phone TEXT,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            assigned_to TEXT NOT NULL,
            dept TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            frequency TEXT NOT NULL,
            due_date TEXT,
            due_time TEXT,
            emp_remark TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(assigned_to) REFERENCES users(username) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            uploaded_by TEXT NOT NULL,
            attachment_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_dept ON tasks(dept)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)")
    migrate_task_columns(conn)
    ensure_default_admin(conn)
    migrate_attachments_from_json(conn)
    conn.commit()
    conn.close()


def authenticate_user(username: str, password: str, role: str = None, dept: str = None):
    conn = get_connection()
    row = conn.execute("SELECT username, password, role, dept FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        conn.close()
        return None
    if role and row["role"] != role:
        conn.close()
        return None
    if dept and row["dept"] != dept:
        conn.close()
        return None
    stored_password = row["password"]
    if verify_password(stored_password, password):
        if not _is_hashed_password(stored_password):
            conn.execute("UPDATE users SET password = ? WHERE username = ?", (hash_password(password), username))
            conn.commit()
        conn.close()
        return dict(row)
    conn.close()
    return None


def get_user(username: str):
    conn = get_connection()
    row = conn.execute("SELECT username, full_name, dept, designation, phone, role FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_all_employees():
    conn = get_connection()
    rows = conn.execute("SELECT username, full_name, dept, designation, phone FROM users WHERE role = 'Employee' ORDER BY full_name").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def fetch_employees_by_dept(dept: str):
    conn = get_connection()
    rows = conn.execute("SELECT username, full_name FROM users WHERE role = 'Employee' AND dept = ? ORDER BY full_name", (dept,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_employee(username: str, password: str, full_name: str, dept: str, designation: str, phone: str):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password, full_name, dept, designation, phone, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (username, hash_password(password), full_name, dept, designation, phone, "Employee", now_str()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_password(username: str, new_password: str):
    conn = get_connection()
    conn.execute("UPDATE users SET password = ? WHERE username = ?", (hash_password(new_password), username))
    conn.commit()
    conn.close()


def delete_user(username: str):
    conn = get_connection()
    attachment_paths = [row["file_path"] for row in conn.execute(
        "SELECT a.file_path FROM attachments a JOIN tasks t ON a.task_id = t.id WHERE t.assigned_to = ?", (username,)
    ).fetchall()]
    for path in attachment_paths:
        try:
            os.remove(path)
        except OSError:
            pass
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()


def create_task(description: str, assigned_to: str, dept: str, priority: str, frequency: str, due_date: str, due_time: str):
    conn = get_connection()
    row = conn.execute(
        "INSERT INTO tasks (description, assigned_to, dept, status, priority, frequency, due_date, due_time, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (description, assigned_to, dept, "Pending", priority, frequency, due_date, due_time, now_str(), now_str()),
    )
    task_id = row.lastrowid
    conn.commit()
    conn.close()
    return task_id


def update_task(task_id: int, description: str, status: str, priority: str, frequency: str, due_date: str, due_time: str, assigned_to: str = None):
    conn = get_connection()
    if assigned_to:
        conn.execute(
            "UPDATE tasks SET description = ?, status = ?, priority = ?, frequency = ?, due_date = ?, due_time = ?, assigned_to = ?, updated_at = ? WHERE id = ?",
            (description, status, priority, frequency, due_date, due_time, assigned_to, now_str(), task_id),
        )
    else:
        conn.execute(
            "UPDATE tasks SET description = ?, status = ?, priority = ?, frequency = ?, due_date = ?, due_time = ?, updated_at = ? WHERE id = ?",
            (description, status, priority, frequency, due_date, due_time, now_str(), task_id),
        )
    conn.commit()
    conn.close()


def update_task_remark_and_status(task_id: int, status: str, remark: str):
    conn = get_connection()
    conn.execute(
        "UPDATE tasks SET status = ?, emp_remark = ?, updated_at = ? WHERE id = ?",
        (status, remark, now_str(), task_id),
    )
    conn.commit()
    conn.close()


def fetch_all_tasks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def fetch_task(task_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_tasks_for_user(username: str):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks WHERE assigned_to = ? ORDER BY due_date IS NULL, due_date, due_time", (username,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def fetch_tasks_for_department(dept: str):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks WHERE dept = ? ORDER BY id DESC", (dept,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_task(task_id: int):
    conn = get_connection()
    paths = [row["file_path"] for row in conn.execute("SELECT file_path FROM attachments WHERE task_id = ?", (task_id,)).fetchall()]
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def save_attachment(task_id: int, uploaded_by: str, attachment_type: str, uploaded_file) -> dict:
    file_name = uploaded_file.name
    file_ext = Path(file_name).suffix
    unique_name = f"{attachment_type}_{task_id}_{secrets.token_hex(10)}{file_ext}"
    file_path = ATTACHMENT_PATH / unique_name
    with open(file_path, "wb") as file_handle:
        file_handle.write(uploaded_file.getbuffer())
    conn = get_connection()
    conn.execute(
        "INSERT INTO attachments (task_id, uploaded_by, attachment_type, file_name, file_path, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
        (task_id, uploaded_by, attachment_type, file_name, str(file_path), now_str()),
    )
    conn.commit()
    conn.close()
    return {
        "file_path": str(file_path),
        "file_name": file_name,
        "uploaded_at": now_str(),
    }


def fetch_attachments(task_id: int, attachment_type: str = None):
    conn = get_connection()
    if attachment_type:
        rows = conn.execute(
            "SELECT * FROM attachments WHERE task_id = ? AND attachment_type = ? ORDER BY id DESC",
            (task_id, attachment_type),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM attachments WHERE task_id = ? ORDER BY id DESC", (task_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def fetch_department_summary():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT dept,
               COUNT(*) AS total_tasks,
               SUM(CASE WHEN status = 'Work Completed' THEN 1 ELSE 0 END) AS completed,
               SUM(CASE WHEN status != 'Work Completed' THEN 1 ELSE 0 END) AS pending,
               SUM(CASE WHEN due_date < ? AND status != 'Work Completed' THEN 1 ELSE 0 END) AS overdue
        FROM tasks
        GROUP BY dept
        """,
        (datetime.now().strftime("%Y-%m-%d"),),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def fetch_task_status_counts():
    conn = get_connection()
    rows = conn.execute(
        "SELECT status, COUNT(*) AS count FROM tasks GROUP BY status ORDER BY count DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

