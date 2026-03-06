"""
LLM Client — Abstracción que soporta Ollama (local) y Claude API
Por defecto usa Ollama; escala a Claude para tareas complejas.
"""
import os
import json
from typing import List, Dict, Optional
import httpx
from anthropic import AsyncAnthropic


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Si el usuario tiene API key de Anthropic, se puede usar Claude para
# tareas complejas. Si no, todo va por Ollama.
USE_CLAUDE = bool(ANTHROPIC_API_KEY)


class LLMClient:
    def __init__(self):
        self.anthropic = AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if USE_CLAUDE else None

    async def chat(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        force_claude: bool = False,
    ) -> Dict:
        """
        Enruta la petición a Ollama o Claude según disponibilidad.
        force_claude=True fuerza el uso de Claude API.
        """
        if force_claude or (USE_CLAUDE and self._needs_advanced_reasoning(messages)):
            return await self._chat_claude(messages, tools, temperature)
        return await self._chat_ollama(messages, tools, temperature)

    def _needs_advanced_reasoning(self, messages: List[Dict]) -> bool:
        """Heurística simple: usa Claude si el mensaje es largo o complejo."""
        last = messages[-1].get("content", "") if messages else ""
        complex_keywords = ["analiza", "redacta", "escribe un", "planifica", "resume"]
        return len(last) > 500 or any(kw in last.lower() for kw in complex_keywords)

    # ── Ollama ──────────────────────────────────────────────────────────────

    async def _chat_ollama(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]],
        temperature: float,
    ) -> Dict:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        msg = data.get("message", {})
        return {
            "content": msg.get("content", ""),
            "tool_calls": msg.get("tool_calls"),
            "usage": {},
        }

    # ── Claude API ──────────────────────────────────────────────────────────

    async def _chat_claude(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]],
        temperature: float,
    ) -> Dict:
        # Separar system prompt
        system = ""
        filtered = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                filtered.append(m)

        kwargs = {
            "model": CLAUDE_MODEL,
            "max_tokens": 2048,
            "temperature": temperature,
            "messages": filtered,
        }
        if system:
            kwargs["system"] = system
        if tools:
            # Convertir formato OpenAI → Anthropic
            kwargs["tools"] = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "input_schema": t["function"].get("parameters", {}),
                }
                for t in tools
            ]

        response = await self.anthropic.messages.create(**kwargs)

        # Convertir respuesta Anthropic → formato interno
        content_text = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    }
                })

        return {
            "content": content_text,
            "tool_calls": tool_calls if tool_calls else None,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }
