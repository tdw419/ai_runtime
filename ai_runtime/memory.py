import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

class RuntimeMemory:
    """
    Manages persistent project state, module status, and action history.
    This is the LLM's working memory/roadmap.
    """
    def __init__(self, project_root: Any):
        project_root = Path(project_root)
        self.db_path = project_root / ".ai_memory" / "runtime_state.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Creates the necessary tables if they don't exist."""
        cur = self.conn.cursor()

        # --- MODULES: Tracks areas of the codebase and their policy (Freeze/Active) ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS modules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, -- e.g., 'Auth', 'Core_Engine'
        path TEXT, -- e.g., 'src/auth'
        status TEXT, -- 'active' | 'frozen' | 'staging'
        priority INTEGER, -- 1-10, higher = more important
        description TEXT,
        updated_at TEXT
        )""")

        # --- STEPS: Planned work items (Tasks) ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module_id INTEGER,
        title TEXT, -- 'Implement Basic Login Route'
        detail TEXT, -- Detailed instruction from human
        status TEXT, -- 'pending' | 'in_progress' | 'done' | 'blocked'
        created_at TEXT,
        updated_at TEXT,
        acceptance_criteria TEXT,
        FOREIGN KEY (module_id) REFERENCES modules(id)
        )""")

        # --- ACTIONS: History of every directive the AI has attempted ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        step_id INTEGER,
        action_type TEXT, -- 'create_file', 'run_command', etc.
        success INTEGER, -- 0 or 1
        created_at TEXT,
        FOREIGN KEY (step_id) REFERENCES steps(id)
        )""")

        # --- NOTES: Human architectural notes ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER,
            note TEXT,
            created_at TEXT,
            FOREIGN KEY (module_id) REFERENCES modules(id)
        )""")

        self.conn.commit()

    def get_or_create_module(self, name: str, path: str, description: str,
    priority: int = 5, status: str = 'staging') -> Dict[str, Any]:
        """Retrieves or creates a module definition."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM modules WHERE name = ?", (name,))
        row = cur.fetchone()
        if row: return dict(row)

        now = datetime.now().isoformat()
        cur.execute("""
        INSERT INTO modules (name, path, status, priority, description, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (name, path, status, priority, description, now))
        self.conn.commit()
        # Retrieve the new record to ensure we get the ID
        cur.execute("SELECT * FROM modules WHERE name = ?", (name,))
        return dict(cur.fetchone())

    def update_module_status(self, module_id: int, status: str, priority: Optional[int] = None):
        """Sets the freeze/active status of a module."""
        cur = self.conn.cursor()
        now = datetime.now().isoformat()
        if priority is not None:
            cur.execute("UPDATE modules SET status = ?, priority = ?, updated_at = ? WHERE id = ?",
            (status, priority, now, module_id))
        else:
            cur.execute("UPDATE modules SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, module_id))
        self.conn.commit()

    def create_step(self, module_id: int, title: str, detail: str, acceptance_criteria: str) -> Dict[str, Any]:
        """Creates a new task for the AI to work on."""
        cur = self.conn.cursor()
        now = datetime.now().isoformat()
        cur.execute("""
        INSERT INTO steps (module_id, title, detail, status, created_at, updated_at, acceptance_criteria)
        VALUES (?, ?, ?, 'pending', ?, ?, ?)
        """, (module_id, title, detail, now, now, acceptance_criteria))
        self.conn.commit()
        cur.execute("SELECT * FROM steps WHERE rowid = last_insert_rowid()")
        return dict(cur.fetchone())

    def get_context_summary(self) -> str:
        """Generates a text summary of all active and frozen modules for the LLM prompt."""
        cur = self.conn.cursor()
        cur.execute("SELECT name, path, status, priority, description FROM modules ORDER BY priority DESC, name ASC")

        summary = ["\n--- Project Module Status ---"]

        for row in cur.fetchall():
            summary.append(f"• [{(row['status']).upper():<7}] {row['name']} (Priority: {row['priority']})")
            summary.append(f" Path: {row['path']}")
            summary.append(f" Description: {row['description']}")

        cur.execute("SELECT m.name, s.title, s.status FROM steps s JOIN modules m ON s.module_id = m.id WHERE s.status != 'done' ORDER BY s.id DESC")
        active_steps = cur.fetchall()

        if active_steps:
            summary.append("\n--- Current Active Tasks ---")
            for row in active_steps:
                summary.append(f"• [{row['status'].upper():<7}] {row['title']} (Module: {row['name']})")

        # Add notes to context
        cur.execute("SELECT m.name, n.note FROM notes n JOIN modules m ON n.module_id = m.id ORDER BY n.created_at DESC LIMIT 5")
        notes = cur.fetchall()
        if notes:
            summary.append("\n--- Recent Architectural Notes ---")
            for row in notes:
                summary.append(f"• ({row['name']}) {row['note']}")

        return "\n".join(summary)

    def is_path_frozen(self, filepath: str) -> bool:
        """Check if a given file path belongs to a frozen module."""
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM modules WHERE ? LIKE path || '%' AND status = 'frozen'", (filepath,))
        return cur.fetchone() is not None

    def add_note(self, module_id: int, note: str):
        """Adds a human-provided note to a module."""
        cur = self.conn.cursor()
        now = datetime.now().isoformat()
        cur.execute("INSERT INTO notes (module_id, note, created_at) VALUES (?, ?, ?)", (module_id, note, now))
        self.conn.commit()

    def list_modules(self) -> List[Dict[str, Any]]:
        """Lists all modules."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM modules ORDER BY name")
        return [dict(row) for row in cur.fetchall()]

    def get_active_steps(self) -> List[Dict[str, Any]]:
        """Returns a list of all steps that are not 'done'."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT s.*, m.name as module_name
            FROM steps s
            JOIN modules m ON s.module_id = m.id
            WHERE s.status != 'done'
            ORDER BY m.priority DESC, s.created_at ASC
        """)
        return [dict(row) for row in cur.fetchall()]

    def get_recent_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns a list of the most recent actions."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM actions ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]

    def log_action(self, step_id: int, action_type: str, params: Dict, result: Dict, success: bool):
        """Logs an action to the database."""
        # This method is a placeholder as the action logging is handled in the SandboxRuntime
        pass

    def get_step_details(self, step_id: int) -> Optional[Dict[str, Any]]:
        """Gets the details for a single step."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM steps WHERE id = ?", (step_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_step_status(self, step_id: int, status: str):
        """Updates the status of a step."""
        cur = self.conn.cursor()
        now = datetime.now().isoformat()
        cur.execute("UPDATE steps SET status = ?, updated_at = ? WHERE id = ?", (status, now, step_id))
        self.conn.commit()

    def get_next_step(self) -> Optional[Dict[str, Any]]:
        """Gets the next pending step to work on."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM steps WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else None

    def freeze_module(self, module_name: str):
        """Freezes a module by name."""
        cur = self.conn.cursor()
        cur.execute("UPDATE modules SET status = 'frozen' WHERE name = ?", (module_name,))
        self.conn.commit()

    def unfreeze_module(self, module_name: str):
        """Unfreezes a module by name."""
        cur = self.conn.cursor()
        cur.execute("UPDATE modules SET status = 'active' WHERE name = ?", (module_name,))
        self.conn.commit()

    def close(self):
        self.conn.close()
