"""
Agent Core — Orquestador principal de Jarvis

Con Claude Agent SDK el loop agéntico (tool calling, razonamiento multi-step)
lo gestiona el propio SDK internamente. Core solo necesita:
  1. Construir el prompt con contexto
  2. Pasar los MCP servers disponibles
  3. Guardar la sesión en memoria para continuidad
"""
import uuid
from typing import List, Dict, Optional

from src.agent.llm import LLMClient
from src.memory.store import MemoryStore
from src.connectors.mcp_registry import MCPRegistry


SYSTEM_PROMPT = """Eres Jarvis, un asistente personal de IA siempre activo en el PC de tu usuario.
Tienes acceso nativo a herramientas para: calendario, email, domótica, ficheros locales,
búsqueda web, gestión de proyectos y APIs externas.

Reglas:
- Razona paso a paso antes de actuar
- Usa las herramientas disponibles sin pedir permiso para tareas rutinarias
- Sé conciso y directo; evita respuestas largas si no las piden
- Responde siempre en el idioma del usuario (español por defecto)
- Si no puedes hacer algo, dilo claramente y sugiere alternativas
"""


class AgentCore:
    def __init__(self, memory: MemoryStore):
        self.memory = memory
        self.llm = LLMClient()
        self.mcp = MCPRegistry()

    async def run(
        self,
        messages: List[Dict],
        conversation_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict:
        conv_id = conversation_id or str(uuid.uuid4())

        # Obtener session_id de Claude si existe para esta conversación
        claude_session = self.memory.get_claude_session(conv_id)

        # Construir prompt incluyendo historial reciente como contexto
        history = self.memory.get_history(conv_id, max_messages=10)
        user_prompt = self._build_prompt(messages, history)

        # Obtener servidores MCP activos
        mcp_servers = self.mcp.get_active_servers()

        # Llamar al LLM (SDK o Ollama)
        response = await self.llm.chat(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            mcp_servers=mcp_servers if mcp_servers else None,
            session_id=claude_session,
        )

        assistant_content = response.get("content", "")
        new_session_id = response.get("session_id")

        # Persistir sesión Claude para continuidad de conversación
        if new_session_id:
            self.memory.set_claude_session(conv_id, new_session_id)

        # Guardar en memoria
        for msg in messages:
            if msg["role"] in ("user", "assistant"):
                self.memory.add_message(conv_id, msg["role"], msg["content"])
        self.memory.add_message(conv_id, "assistant", assistant_content)

        cost = response.get("cost_usd")
        usage = response.get("usage", {})

        return {
            "id":     f"jarvis-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "model":  f"jarvis/{self.llm.backend}",
            "choices": [{
                "index":        0,
                "message":      {"role": "assistant", "content": assistant_content},
                "finish_reason": "stop",
            }],
            "usage": usage,
            # Extras informativos (no estándar OpenAI, pero útiles)
            "jarvis_meta": {
                "conversation_id": conv_id,
                "claude_session":  new_session_id,
                "cost_usd":        cost,
                "turns":           response.get("turns"),
                "backend":         self.llm.backend,
            },
        }

    def _build_prompt(self, messages: List[Dict], history: List[Dict]) -> str:
        """Construye el prompt final con historial si Ollama está activo."""
        # Con Claude SDK el historial se gestiona via session_id, no hace falta aquí
        if self.llm.backend == "claude-sdk":
            user_msgs = [m["content"] for m in messages if m["role"] == "user"]
            return user_msgs[-1] if user_msgs else ""

        # Para Ollama: incluir historial en el prompt
        lines = []
        for m in history[-6:]:
            prefix = "Usuario" if m["role"] == "user" else "Jarvis"
            lines.append(f"{prefix}: {m['content']}")
        for m in messages:
            if m["role"] == "user":
                lines.append(f"Usuario: {m['content']}")
        return "\n".join(lines)
