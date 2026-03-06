"""
Conector API genérico — llama a cualquier API externa con configuración dinámica
"""
import os
import json
from typing import List, Dict, Any
import httpx

from src.connectors.base import BaseConnector


class APIConnector(BaseConnector):

    def get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "api_call",
                    "description": "Llama a cualquier API HTTP externa. Útil para integraciones personalizadas.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL completa del endpoint"},
                            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"], "default": "GET"},
                            "headers": {"type": "object", "description": "Headers HTTP (ej: Authorization)"},
                            "body": {"type": "object", "description": "Body JSON para POST/PUT"},
                            "params": {"type": "object", "description": "Query params para GET"}
                        },
                        "required": ["url"]
                    }
                }
            }
        ]

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        method = args.get("method", "GET").upper()
        headers = args.get("headers", {})
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method=method,
                url=args["url"],
                headers=headers,
                json=args.get("body"),
                params=args.get("params"),
            )
            try:
                return resp.json()
            except Exception:
                return {"status_code": resp.status_code, "text": resp.text[:2000]}
