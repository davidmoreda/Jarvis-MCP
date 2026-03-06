"""
Conector Projects — gestión de proyectos, tareas y brainstorming
Almacena en SQLite local. Simple pero efectivo.
"""
import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Any

from src.connectors.base import BaseConnector

DB_PATH = os.getenv("PROJECTS_DB_PATH", "data/projects.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, name TEXT, description TEXT,
            status TEXT DEFAULT 'active', created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, project_id TEXT, title TEXT,
            description TEXT, status TEXT DEFAULT 'todo',
            priority TEXT DEFAULT 'medium', created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY, project_id TEXT, content TEXT,
            tags TEXT, created_at TEXT
        )
    """)
    conn.commit()
    return conn


class ProjectsConnector(BaseConnector):

    def get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "project_list",
                    "description": "Lista todos los proyectos activos.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "project_create",
                    "description": "Crea un nuevo proyecto.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "task_add",
                    "description": "Añade una tarea a un proyecto.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "priority": {"type": "string", "enum": ["low", "medium", "high"], "default": "medium"}
                        },
                        "required": ["project_id", "title"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "task_list",
                    "description": "Lista las tareas de un proyecto.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "status": {"type": "string", "enum": ["todo", "in_progress", "done", "all"], "default": "todo"}
                        },
                        "required": ["project_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "note_add",
                    "description": "Añade una nota o idea a un proyecto (útil para brainstorming).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "content": {"type": "string"},
                            "tags": {"type": "string", "description": "Tags separados por coma"}
                        },
                        "required": ["project_id", "content"]
                    }
                }
            }
        ]

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        conn = _get_conn()
        now = datetime.utcnow().isoformat()

        if tool_name == "project_list":
            rows = conn.execute("SELECT * FROM projects WHERE status='active'").fetchall()
            return [dict(r) for r in rows]

        elif tool_name == "project_create":
            pid = str(uuid.uuid4())[:8]
            conn.execute(
                "INSERT INTO projects VALUES (?,?,?,?,?)",
                (pid, args["name"], args.get("description", ""), "active", now)
            )
            conn.commit()
            return {"created": True, "project_id": pid, "name": args["name"]}

        elif tool_name == "task_add":
            tid = str(uuid.uuid4())[:8]
            conn.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?)",
                (tid, args["project_id"], args["title"], args.get("description", ""), "todo", args.get("priority", "medium"), now)
            )
            conn.commit()
            return {"created": True, "task_id": tid}

        elif tool_name == "task_list":
            status = args.get("status", "todo")
            query = "SELECT * FROM tasks WHERE project_id=?"
            params = [args["project_id"]]
            if status != "all":
                query += " AND status=?"
                params.append(status)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

        elif tool_name == "note_add":
            nid = str(uuid.uuid4())[:8]
            conn.execute(
                "INSERT INTO notes VALUES (?,?,?,?,?)",
                (nid, args["project_id"], args["content"], args.get("tags", ""), now)
            )
            conn.commit()
            return {"created": True, "note_id": nid}
