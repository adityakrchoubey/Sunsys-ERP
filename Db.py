# Full PostgreSQL/Supabase Converted Database Code

Replace your entire current `db.py` or database file with this code.

```python
import os
import json
import hashlib
import secrets
from datetime import datetime
from pathlib import Path

import streamlit as st
from sqlalchemy import create_engine, text

# =========================
# DATABASE CONFIG
# =========================

DATABASE_URL = st.secrets["DATABASE_URL"]

engine = create_engine(DATABASE_URL)

# =========================
# FILE STORAGE
# =========================

DATA_FOLDER = Path("data")
ATTACHMENT_PATH = DATA_FOLDER / "attachments"

DATA_FOLDER.mkdir(exist_ok=True)
ATTACHMENT_PATH.mkdir(parents=True, exist_ok=True)

# =========================
# PASSWORD FUNCTIONS
# =========================


def _is_hashed_password(value: str) -> bool:
    return isinstance(value, str) and value.startswith("pbkdf2_sha256$") and value.count("$") == 3



def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 120000

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )

    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"



def verify_password(stored_value: str, raw_password: str) -> bool:
    if not stored_value or not raw_password:
        return False

    if _is_hashed_password(stored_value):
        _, iterations, salt, hash_hex = stored_value.split("$", 3)

        new_hash = hashlib.pbkdf2_hmac(
            "sha256",
            raw_password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()

        return secrets.compare_digest(new_hash, hash_hex)

    return stored_value == raw_password


# =========================
# TIME FUNCTION
# =========================


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =========================
# INITIALIZE DATABASE
# =========================


def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
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
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
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
                updated_at TEXT NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS attachments (
                id SERIAL PRIMARY KEY,
                task_id INTEGER,
                uploaded_by TEXT,
                attachment_type TEXT,
                file_name TEXT,
                file_path TEXT,
                uploaded_at TEXT
            )
        """))

        # Create default admin
        admin = conn.execute(
            text("SELECT * FROM users WHERE username = :username"),
            {"username": "admin"},
        ).mappings().fetchone()

        if not admin:
            conn.execute(
                text("""
                    INSERT INTO users (
                        username,
                        password,
                        full_name,
                        dept,
                        designation,
                        phone,
                        role,
                        created_at
                    )
                    VALUES (
                        :username,
                        :password,
                        :full_name,
                        :dept,
                        :designation,
                        :phone,
                        :role,
                        :created_at
                    )
                """),
                {
                    "username": "admin",
                    "password": hash_password("admin2026"),
                    "full_name": "HR Manager",
                    "dept": "HR & Admin",
                    "designation": "HR Head",
                    "phone": "",
                    "role": "Admin",
                    "created_at": now_str(),
                },
            )


# =========================
# AUTHENTICATION
# =========================


def authenticate_user(username: str, password: str, role: str = None, dept: str = None):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT username, password, role, dept FROM users WHERE username = :username"),
            {"username": username},
        ).mappings().fetchone()

    if not row:
        return None

    if role and row["role"] != role:
        return None

    if dept and row["dept"] != dept:
        return None

    stored_password = row["password"]

    if verify_password(stored_password, password):
        return dict(row)

    return None


# =========================
# USERS
# =========================


def get_user(username: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT username, full_name, dept,
                designation, phone, role
                FROM users
                WHERE username = :username
            """),
            {"username": username},
        ).mappings().fetchone()

    return dict(row) if row else None



def fetch_all_employees():
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT username, full_name,
                dept, designation, phone
                FROM users
                WHERE role = 'Employee'
                ORDER BY full_name
            """)
        ).mappings().all()

    return [dict(row) for row in rows]



def fetch_employees_by_dept(dept: str):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT username, full_name
                FROM users
                WHERE role = 'Employee'
                AND dept = :dept
                ORDER BY full_name
            """),
            {"dept": dept},
        ).mappings().all()

    return [dict(row) for row in rows]



def add_employee(username, password, full_name, dept, designation, phone):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO users (
                        username,
                        password,
                        full_name,
                        dept,
                        designation,
                        phone,
                        role,
                        created_at
                    )
                    VALUES (
                        :username,
                        :password,
                        :full_name,
                        :dept,
                        :designation,
                        :phone,
                        :role,
                        :created_at
                    )
                """),
                {
                    "username": username,
                    "password": hash_password(password),
                    "full_name": full_name,
                    "dept": dept,
                    "designation": designation,
                    "phone": phone,
                    "role": "Employee",
                    "created_at": now_str(),
                },
            )

        return True

    except Exception:
        return False



def update_password(username: str, new_password: str):
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE users
                SET password = :password
                WHERE username = :username
            """),
            {
                "password": hash_password(new_password),
                "username": username,
            },
        )



def delete_user(username: str):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM users WHERE username = :username"),
            {"username": username},
        )


# =========================
# TASKS
# =========================


def create_task(description, assigned_to, dept, priority, frequency, due_date, due_time):
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO tasks (
                    description,
                    assigned_to,
                    dept,
                    status,
                    priority,
                    frequency,
                    due_date,
                    due_time,
                    created_at,
                    updated_at
                )
                VALUES (
                    :description,
                    :assigned_to,
                    :dept,
                    :status,
                    :priority,
                    :frequency,
                    :due_date,
                    :due_time,
                    :created_at,
                    :updated_at
                )
                RETURNING id
            """),
            {
                "description": description,
                "assigned_to": assigned_to,
                "dept": dept,
                "status": "Pending",
                "priority": priority,
                "frequency": frequency,
                "due_date": due_date,
                "due_time": due_time,
                "created_at": now_str(),
                "updated_at": now_str(),
            },
        )

        task_id = result.fetchone()[0]

    return task_id



def fetch_all_tasks():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM tasks ORDER BY id DESC")
        ).mappings().all()

    return [dict(row) for row in rows]



def fetch_tasks_for_user(username: str):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT *
                FROM tasks
                WHERE assigned_to = :username
                ORDER BY id DESC
            """),
            {"username": username},
        ).mappings().all()

    return [dict(row) for row in rows]



def update_task_remark_and_status(task_id: int, status: str, remark: str):
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE tasks
                SET status = :status,
                    emp_remark = :remark,
                    updated_at = :updated_at
                WHERE id = :task_id
            """),
            {
                "status": status,
                "remark": remark,
                "updated_at": now_str(),
                "task_id": task_id,
            },
        )



def delete_task(task_id: int):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM tasks WHERE id = :task_id"),
            {"task_id": task_id},
        )


# =========================
# ATTACHMENTS
# =========================


def save_attachment(task_id, uploaded_by, attachment_type, uploaded_file):
    file_name = uploaded_file.name
    file_ext = Path(file_name).suffix

    unique_name = f"{attachment_type}_{task_id}_{secrets.token_hex(10)}{file_ext}"

    file_path = ATTACHMENT_PATH / unique_name

    with open(file_path, "wb") as file_handle:
        file_handle.write(uploaded_file.getbuffer())

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO attachments (
                    task_id,
                    uploaded_by,
                    attachment_type,
                    file_name,
                    file_path,
                    uploaded_at
                )
                VALUES (
                    :task_id,
                    :uploaded_by,
                    :attachment_type,
                    :file_name,
                    :file_path,
                    :uploaded_at
                )
            """),
            {
                "task_id": task_id,
                "uploaded_by": uploaded_by,
                "attachment_type": attachment_type,
                "file_name": file_name,
                "file_path": str(file_path),
                "uploaded_at": now_str(),
            },
        )

    return {
        "file_path": str(file_path),
        "file_name": file_name,
        "uploaded_at": now_str(),
    }



def fetch_attachments(task_id: int, attachment_type: str = None):
    with engine.connect() as conn:
        if attachment_type:
            rows = conn.execute(
                text("""
                    SELECT *
                    FROM attachments
                    WHERE task_id = :task_id
                    AND attachment_type = :attachment_type
                    ORDER BY id DESC
                """),
                {
                    "task_id": task_id,
                    "attachment_type": attachment_type,
                },
            ).mappings().all()
        else:
            rows = conn.execute(
                text("""
                    SELECT *
                    FROM attachments
                    WHERE task_id = :task_id
                    ORDER BY id DESC
                """),
                {"task_id": task_id},
            ).mappings().all()

    return [dict(row) for row in rows]


# =========================
# DASHBOARD SUMMARY
# =========================


def fetch_department_summary():
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT dept,
                       COUNT(*) AS total_tasks,
                       SUM(CASE WHEN status = 'Work Completed' THEN 1 ELSE 0 END) AS completed,
                       SUM(CASE WHEN status != 'Work Completed' THEN 1 ELSE 0 END) AS pending
                FROM tasks
                GROUP BY dept
            """)
        ).mappings().all()

    return [dict(row) for row in rows]



def fetch_task_status_counts():
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT status,
                       COUNT(*) AS count
                FROM tasks
                GROUP BY status
                ORDER BY count DESC
            """)
        ).mappings().all()

    return [dict(row) for row in rows]





