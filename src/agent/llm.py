"""
LLM Client — Claude Agent SDK nativo (+ fallback Ollama)

Autenticación:
  - Opción A (recomendada): login con tu cuenta claude.ai → usa tu suscripción Pro
      docker exec -it jarvis-api claude auth login
  - Opción B: ANTHROPIC_API_KEY en .env → paga por tokens
  - Fallback: Ollama local si Claude no está disponible

El SDK maneja el agentic loop completo: tool calling, sesiones,
streaming y coste de manera nativa. No necesitamos implementarlo.
"""
import os
import asyncio
import uuid
import json
from typing import List, Dict, Optional, AsyncIterator

# ── Detección de backend ────────────────────────────────────────────────────

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.2")
CLAUDE_MODEL    = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# El SDK usa la key si está presente; si no, usa el login OAuth del CLI
os.environ.setdefault("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)


def _claude_cli_available() -> bool:
    """Comprueba si el claude CLI está instalado Y autenticado."""
    import shutil, subprocess
    if not shutil.which("claude"):
        return False
    try:
        # --version solo comprueba que existe
        result = subprocess.run(
            ["claude", "--version"], capture_output=True, timeout=5
        )
        if result.returncode != 0:
            return False
        # Comprueba que hay sesión activa (auth)
        auth = subprocess.run(
            ["claude", "config", "get", "oauthToken"],
            capture_output=True, timeout=5
        )
        # Si hay token OAuth O hay ANTHROPIC_API_KEY en el entorno, está autenticado
        has_oauth = auth.returncode == 0 and auth.stdout.strip()
        has_api_key = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
        return has_oauth or has_api_key
    except Exception:
        return False


def _sdk_available() -> bool:
    try:
        import claude_code_sdk  # noqa
        return True
    except ImportError:
        return False


# ── Cliente Claude Agent SDK ────────────────────────────────────────────────

class ClaudeSDKClient:
    """
    Wrapper sobre claude_code_sdk.query().

    El SDK lanza el claude CLI como subproceso y devuelve un
    AsyncIterator de mensajes tipados (AssistantMessage, ResultMessage…).
    Toda la lógica de tool calling y sesiones es nativa del SDK.
    """

    def __init__(self):
        from claude_code_sdk import ClaudeCodeOptions
        self._options_cls = ClaudeCodeOptions

    def _build_options(
        self,
        tools: Optional[List[Dict]] = None,
        mcp_servers: Optional[Dict] = None,
        session_id: Optional[str] = None,
        max_turns: int = 10,
    ):
        """Convierte nuestros parámetros al formato ClaudeCodeOptions."""
        kwargs = dict(
            model=CLAUDE_MODEL,
            max_turns=max_turns,
            # Permisos: bypassPermissions para uso local de confianza
            permission_mode="bypassPermissions",
        )
        if session_id:
            kwargs["resume"] = session_id
        if mcp_servers:
            kwargs["mcp_servers"] = mcp_servers
        # Si hay tools definidas como allowed_tools (nombres nativos claude)
        if tools:
            native_tools = [t.get("native_name") for t in tools if t.get("native_name")]
            if native_tools:
                kwargs["allowed_tools"] = native_tools

        return self._options_cls(**kwargs)

    async def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        mcp_servers: Optional[Dict] = None,
        session_id: Optional[str] = None,
        max_turns: int = 10,
    ) -> Dict:
        """
        Ejecuta una query y devuelve la respuesta consolidada.
        Retorna: { content, session_id, cost_usd, usage, turns }
        """
        from claude_code_sdk import query, AssistantMessage, ResultMessage, TextBlock

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"<system>{system_prompt}</system>\n\n{prompt}"

        options = self._build_options(
            mcp_servers=mcp_servers,
            session_id=session_id,
            max_turns=max_turns,
        )

        result_text = ""
        new_session_id = session_id
        cost = None
        usage = {}
        turns = 0

        async for msg in query(prompt=full_prompt, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        result_text += block.text

            elif isinstance(msg, ResultMessage):
                new_session_id = msg.session_id or new_session_id
                cost = msg.total_cost_usd
                turns = msg.num_turns
                if msg.usage:
                    usage = {
                        "input_tokens":  msg.usage.get("input_tokens", 0),
                        "output_tokens": msg.usage.get("output_tokens", 0),
                    }

        return {
            "content":    result_text,
            "session_id": new_session_id,
            "cost_usd":   cost,
            "usage":      usage,
            "turns":      turns,
            "tool_calls": None,  # el SDK los resuelve internamente
        }

    async def query_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        mcp_servers: Optional[Dict] = None,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[Dict]:
        """Streaming: yield cada chunk de texto a medida que llega."""
        from claude_code_sdk import query, AssistantMessage, ResultMessage, TextBlock

        full_prompt = f"<system>{system_prompt}</system>\n\n{prompt}" if system_prompt else prompt
        options = self._build_options(mcp_servers=mcp_servers, session_id=session_id)

        async for msg in query(prompt=full_prompt, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock) and block.text:
                        yield {"type": "text", "text": block.text}
            elif isinstance(msg, ResultMessage):
                yield {
                    "type":       "done",
                    "session_id": msg.session_id,
                    "cost_usd":   msg.total_cost_usd,
                    "turns":      msg.num_turns,
                }


# ── Fallback: Ollama ────────────────────────────────────────────────────────

class OllamaClient:
    """Cliente Ollama como fallback cuando Claude CLI no está disponible."""

    async def query(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
    ) -> Dict:
        import httpx
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.7},
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        msg = data.get("message", {})
        return {
            "content":    msg.get("content", ""),
            "tool_calls": msg.get("tool_calls"),
            "session_id": None,
            "cost_usd":   None,
            "usage":      {},
        }


# ── Façade principal ────────────────────────────────────────────────────────

class LLMClient:
    """
    Punto de entrada único para el agente.
    Usa Claude Agent SDK si está disponible, si no cae a Ollama.
    """

    def __init__(self):
        self._use_sdk = _sdk_available() and _claude_cli_available()
        if self._use_sdk:
            self._claude = ClaudeSDKClient()
            print("✅ LLM backend: Claude Agent SDK (nativo)")
        else:
            self._ollama = OllamaClient()
            print("⚠️  LLM backend: Ollama (Claude CLI no disponible)")

    @property
    def backend(self) -> str:
        return "claude-sdk" if self._use_sdk else "ollama"

    async def chat(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        mcp_servers: Optional[Dict] = None,
        session_id: Optional[str] = None,
    ) -> Dict:
        if self._use_sdk:
            try:
                system = next((m["content"] for m in messages if m["role"] == "system"), None)
                user_msgs = [m["content"] for m in messages if m["role"] == "user"]
                prompt = user_msgs[-1] if user_msgs else ""
                return await self._claude.query(
                    prompt=prompt,
                    system_prompt=system,
                    mcp_servers=mcp_servers,
                    session_id=session_id,
                )
            except Exception as e:
                print(f"⚠️  Claude SDK falló ({e}), cayendo a Ollama...")
                if not hasattr(self, '_ollama'):
                    self._ollama = OllamaClient()
                return await self._ollama.query(messages=messages, tools=tools)
        else:
            return await self._ollama.query(messages=messages, tools=tools)
