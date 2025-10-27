"""
Runtime Memory System - Persistent state management with SQLite
"""
import sqlite3
import json
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


class RuntimeMemory:
    """Manages persistent state for the AI runtime using SQLite"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema"""
        cur = self.conn.cursor()

        # Modules table - tracks areas of codebase and edit policies
        cur.execute("""
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            path TEXT,
            status TEXT,
            priority INTEGER,
            description TEXT,
            updated_at TEXT
        )
        """)

        # Steps table - planned work items/milestones
        cur.execute("""
        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER,
            title TEXT,
            detail TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (module_id) REFERENCES modules(id)
        )
        """)

        # Actions table - every atomic directive the AI tried
        cur.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            step_id INTEGER,
            action_type TEXT,
            params_json TEXT,
            result_json TEXT,
            success INTEGER,
            created_at TEXT,
            FOREIGN KEY (step_id) REFERENCES steps(id)
        )
        """)

        # Notes table - human guidance/overrides
        cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER,
            note TEXT,
            created_at TEXT,
            FOREIGN KEY (module_id) REFERENCES modules(id)
        )
        """)

        self.conn.commit()

    def _now(self) -> str:
        """Get current UTC timestamp"""
        return datetime.datetime.utcnow().isoformat()

    # ===== MODULE MANAGEMENT =====

    def get_or_create_module(self, name: str, path: str, description: str,
                             default_status="staging", default_priority=5) -> Dict[str, Any]:
        """Get existing module or create new one"""
        cur = self.conn.cursor()

        cur.execute("SELECT * FROM modules WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return dict(row)

        cur.execute("""
            INSERT INTO modules (name, path, status, priority, description, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, path, default_status, default_priority, description, self._now()))

        self.conn.commit()

        cur.execute("SELECT * FROM modules WHERE name = ?", (name,))
        return dict(cur.fetchone())

    def update_module_status(self, module_id: int, status: str, priority: Optional[int] = None):
        """Update module status (frozen/active/staging) and optionally priority"""
        cur = self.conn.cursor()
        if priority is not None:
            cur.execute("""
                UPDATE modules SET status = ?, priority = ?, updated_at = ?
                WHERE id = ?
            """, (status, priority, self._now(), module_id))
        else:
            cur.execute("""
                UPDATE modules SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status, self._now(), module_id))
        self.conn.commit()

    def freeze_module(self, module_name: str):
        """Freeze a module to prevent AI edits"""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE modules SET status = 'frozen', updated_at = ?
            WHERE name = ?
        """, (self._now(), module_name))
        self.conn.commit()

    def unfreeze_module(self, module_name: str):
        """Unfreeze a module to allow AI edits"""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE modules SET status = 'active', updated_at = ?
            WHERE name = ?
        """, (self._now(), module_name))
        self.conn.commit()

    def is_path_frozen(self, filepath: str) -> bool:
        """Check if a file path belongs to a frozen module"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT status FROM modules
            WHERE ? LIKE path || '%' AND status = 'frozen'
        """, (filepath,))
        return cur.fetchone() is not None

    def list_modules(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all modules, optionally filtered by status"""
        cur = self.conn.cursor()
        if status:
            cur.execute("SELECT * FROM modules WHERE status = ? ORDER BY priority DESC", (status,))
        else:
            cur.execute("SELECT * FROM modules ORDER BY priority DESC")
        return [dict(row) for row in cur.fetchall()]

    # ===== STEP/TASK MANAGEMENT =====

    def create_step(self, module_id: int, title: str, detail: str) -> Dict[str, Any]:
        """Create a new step/task"""
        cur = self.conn.cursor()
        now = self._now()
        cur.execute("""
            INSERT INTO steps (module_id, title, detail, status, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', ?, ?)
        """, (module_id, title, detail, now, now))
        self.conn.commit()

        cur.execute("SELECT * FROM steps WHERE id = ?", (cur.lastrowid,))
        return dict(cur.fetchone())

    def update_step_status(self, step_id: int, status: str):
        """Update step status (pending/in_progress/done/blocked)"""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE steps SET status = ?, updated_at = ?
            WHERE id = ?
        """, (status, self._now(), step_id))
        self.conn.commit()

    def get_active_steps(self) -> List[Dict[str, Any]]:
        """Get all pending or in-progress steps"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT s.*, m.name as module_name, m.priority as module_priority
            FROM steps s
            JOIN modules m ON s.module_id = m.id
            WHERE s.status IN ('pending', 'in_progress')
            ORDER BY m.priority DESC, s.created_at ASC
        """)
        return [dict(row) for row in cur.fetchall()]

    def get_next_step(self) -> Optional[Dict[str, Any]]:
        """Get the highest priority pending step"""
        steps = self.get_active_steps()
        return steps[0] if steps else None

    # ===== ACTION TRACKING =====

    def log_action(self, step_id: Optional[int], action_type: str,
                   params: Dict[str, Any], result: Dict[str, Any], success: bool):
        """Log an action attempt and result"""
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO actions (step_id, action_type, params_json, result_json, success, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (step_id, action_type, json.dumps(params), json.dumps(result),
              1 if success else 0, self._now()))
        self.conn.commit()

    def get_recent_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent actions"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM actions
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]

    # ===== NOTES/GUIDANCE =====

    def add_note(self, module_id: int, note: str):
        """Add a human note/guidance for a module"""
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO notes (module_id, note, created_at)
            VALUES (?, ?, ?)
        """, (module_id, note, self._now()))
        self.conn.commit()

    def get_notes_for_module(self, module_id: int) -> List[Dict[str, Any]]:
        """Get all notes for a module"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM notes
            WHERE module_id = ?
            ORDER BY created_at DESC
        """, (module_id,))
        return [dict(row) for row in cur.fetchall()]

    # ===== CONTEXT GENERATION FOR LLM =====

    def get_context_summary(self) -> str:
        """Generate a summary of current state for the LLM"""
        modules = self.list_modules()
        active_steps = self.get_active_steps()
        recent_actions = self.get_recent_actions(limit=5)

        summary = "=== PROJECT STATE ===\n\n"

        summary += "MODULES:\n"
        for mod in modules:
            status_icon = {
                'frozen': '🔒',
                'active': '✅',
                'staging': '🚧'
            }.get(mod['status'], '❓')
            summary += f"  {status_icon} {mod['name']} (priority {mod['priority']}): {mod['description']}\n"

        summary += "\nACTIVE STEPS:\n"
        if active_steps:
            for step in active_steps[:5]:
                summary += f"  • [{step['status']}] {step['title']} (module: {step['module_name']})\n"
        else:
            summary += "  (no active steps)\n"

        summary += "\nRECENT ACTIONS:\n"
        for action in recent_actions:
            success_icon = '✅' if action['success'] else '❌'
            summary += f"  {success_icon} {action['action_type']}\n"

        return summary

    def close(self):
        """Close database connection"""
        self.conn.close()
