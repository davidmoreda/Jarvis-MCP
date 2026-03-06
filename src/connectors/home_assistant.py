"""
Conector Home Assistant — control de domótica via REST API
"""
import os
from typing import List, Dict, Any
import httpx

from src.connectors.base import BaseConnector

HA_URL = os.getenv("HOME_ASSISTANT_URL", "http://homeassistant.local:8123")
HA_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN", "")


class HomeAssistantConnector(BaseConnector):

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }

    def get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "ha_get_states",
                    "description": "Obtiene el estado de todos los dispositivos o de uno en concreto.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_id": {
                                "type": "string",
                                "description": "ID de la entidad (ej: light.salon). Si se omite, devuelve todos."
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ha_call_service",
                    "description": "Llama a un servicio de Home Assistant (ej: encender luz, activar escena).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "domain": {"type": "string", "description": "Dominio del servicio (ej: light, switch, scene, climate)"},
                            "service": {"type": "string", "description": "Nombre del servicio (ej: turn_on, turn_off, toggle)"},
                            "entity_id": {"type": "string", "description": "ID de la entidad a controlar"},
                            "extra_data": {"type": "object", "description": "Datos adicionales (ej: brightness, temperature)"}
                        },
                        "required": ["domain", "service", "entity_id"]
                    }
                }
            }
        ]

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=10) as client:
            if tool_name == "ha_get_states":
                entity_id = args.get("entity_id")
                url = f"{HA_URL}/api/states"
                if entity_id:
                    url += f"/{entity_id}"
                resp = await client.get(url, headers=self._headers)
                resp.raise_for_status()
                return resp.json()

            elif tool_name == "ha_call_service":
                domain = args["domain"]
                service = args["service"]
                data = {"entity_id": args["entity_id"]}
                data.update(args.get("extra_data", {}))
                url = f"{HA_URL}/api/services/{domain}/{service}"
                resp = await client.post(url, headers=self._headers, json=data)
                resp.raise_for_status()
                return {"success": True, "result": resp.json()}
