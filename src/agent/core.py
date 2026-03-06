"""
Agent Core — Agentic loop con tool calling
Soporta Ollama (local) y Claude API (avanzado)
"""
import json
import uuid
from typing import List, Dict, Any, Optional

from src.agent.llm import LLMClient
from src.memory.store import MemoryStore
from src.connectors.google_calendar import GoogleCalendarConnector
from src.connectors.gmail import GmailConnector
from src.connectors.home_assistant import HomeAssistantConnector
from src.connectors.local_files import LocalFilesConnector
from src.connectors.web_search import WebSearchConnector
from src.connectors.projects import ProjectsConnector
from src.connectors.api_connector import APIConnector


SYSTEM_PROMPT = """Eres Jarvis, un asistente personal de IA siempre activo.
Tienes acceso a herramientas para gestionar el calendario, email, domótica,
ficheros locales, búsqueda web, proyectos y APIs externas.

Razona paso a paso antes de usar cualquier herramienta.
Sé conciso, directo y útil. Responde siempre en el idioma del usuario.
"""


class AgentCore:
    def __init__(self, memory: MemoryStore):
        self.memory = memory
        self.llm = LLMClient()

        # Registrar todos los conectores
        self.connectors = [
            GoogleCalendarConnector(),
            GmailConnector(),
            HomeAssistantConnector(),
            LocalFilesConnector(),
            WebSearchConnector(),
            ProjectsConnector(),
            APIConnector(),
        ]

        # Construir mapa tool_name → conector
        self.tool_map: Dict[str, Any] = {}
        for connector in self.connectors:
            for tool in connector.get_tools():
                self.tool_map[tool["function"]["name"]] = connector

    def _get_all_tools(self) -> List[Dict]:
        tools = []
        for connector in self.connectors:
            tools.extend(connector.get_tools())
        return tools

    async def run(
        self,
        messages: List[Dict],
        conversation_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict:
        conv_id = conversation_id or str(uuid.uuid4())

        # Cargar historial de memoria
        history = self.memory.get_history(conv_id)

        # Construir contexto completo
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        full_messages.extend(history)
        full_messages.extend(messages)

        tools = self._get_all_tools()

        # Agentic loop (máx. 10 iteraciones)
        for _ in range(10):
            response = await self.llm.chat(
                messages=full_messages,
                tools=tools,
                temperature=temperature,
            )

            # Si no hay tool calls → respuesta final
            if not response.get("tool_calls"):
                assistant_content = response["content"]

                # Guardar en memoria
                for msg in messages:
                    self.memory.add_message(conv_id, msg["role"], msg["content"])
                self.memory.add_message(conv_id, "assistant", assistant_content)

                return {
                    "id": f"jarvis-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion",
                    "model": "jarvis",
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": assistant_content},
                        "finish_reason": "stop"
                    }],
                    "usage": response.get("usage", {})
                }

            # Ejecutar tool calls
            full_messages.append({
                "role": "assistant",
                "content": response.get("content", ""),
                "tool_calls": response["tool_calls"]
            })

            for tool_call in response["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])

                connector = self.tool_map.get(tool_name)
                if connector:
                    try:
                        result = await connector.call_tool(tool_name, tool_args)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Tool '{tool_name}' not found"}

                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result, ensure_ascii=False)
                })

        return {
            "id": f"jarvis-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "model": "jarvis",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "Alcanzado el límite de iteraciones del agente."},
                "finish_reason": "stop"
            }],
            "usage": {}
        }
