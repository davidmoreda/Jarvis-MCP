"""
Conector Local Files — leer/escribir ficheros del sistema local
Acceso restringido a directorios permitidos en .env
"""
import os
from pathlib import Path
from typing import List, Dict, Any

from src.connectors.base import BaseConnector

# Directorios permitidos (separados por coma en .env)
_raw = os.getenv("LOCAL_FILES_ALLOWED_DIRS", str(Path.home()))
ALLOWED_DIRS = [Path(d.strip()).resolve() for d in _raw.split(",")]


def _check_allowed(path: Path) -> Path:
    path = path.resolve()
    if not any(str(path).startswith(str(d)) for d in ALLOWED_DIRS):
        raise PermissionError(f"Acceso denegado: {path} no está en los directorios permitidos.")
    return path


class LocalFilesConnector(BaseConnector):

    def get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "file_read",
                    "description": "Lee el contenido de un fichero local.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Ruta absoluta o relativa al fichero"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_write",
                    "description": "Escribe o sobreescribe un fichero local.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Ruta al fichero"},
                            "content": {"type": "string", "description": "Contenido a escribir"},
                            "append": {"type": "boolean", "description": "Si true, añade al final en vez de sobreescribir", "default": False}
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_list",
                    "description": "Lista ficheros y carpetas en un directorio.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Ruta del directorio"},
                            "pattern": {"type": "string", "description": "Patrón glob (ej: *.py)", "default": "*"}
                        },
                        "required": ["path"]
                    }
                }
            }
        ]

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "file_read":
            p = _check_allowed(Path(args["path"]))
            return {"content": p.read_text(encoding="utf-8"), "size": p.stat().st_size}

        elif tool_name == "file_write":
            p = _check_allowed(Path(args["path"]))
            p.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if args.get("append") else "w"
            with open(p, mode, encoding="utf-8") as f:
                f.write(args["content"])
            return {"success": True, "path": str(p)}

        elif tool_name == "file_list":
            p = _check_allowed(Path(args["path"]))
            pattern = args.get("pattern", "*")
            items = list(p.glob(pattern))
            return [{"name": i.name, "type": "dir" if i.is_dir() else "file", "size": i.stat().st_size if i.is_file() else None} for i in items[:50]]
