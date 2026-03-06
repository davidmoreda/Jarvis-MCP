"""
MCP Registry — Registra y gestiona los servidores MCP disponibles.

El Claude Agent SDK acepta mcp_servers como dict con este formato:
{
  "nombre": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-xxx"],
    "env": {"API_KEY": "..."}
  }
}

Aquí centralizamos qué servidores MCP están activos según .env.
"""
import os
from typing import Dict, Optional


class MCPRegistry:
    """
    Construye el dict de mcp_servers a pasar al Claude Agent SDK.
    Solo activa los servidores que tienen sus credenciales configuradas.
    """

    def get_active_servers(self) -> Dict:
        servers = {}

        # ── Google Calendar / Gmail ────────────────────────────────────────
        google_creds = os.getenv("GOOGLE_CREDENTIALS_PATH")
        if google_creds and os.path.exists(google_creds):
            servers["google-calendar"] = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-google-calendar"],
                "env": {
                    "GOOGLE_CREDENTIALS": google_creds,
                    "GOOGLE_TOKEN": os.getenv("GOOGLE_TOKEN_PATH", "credentials/google_token.json"),
                }
            }
            servers["gmail"] = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-gmail"],
                "env": {
                    "GOOGLE_CREDENTIALS": google_creds,
                    "GOOGLE_TOKEN": os.getenv("GOOGLE_TOKEN_PATH", "credentials/google_token.json"),
                }
            }

        # ── Filesystem (ficheros locales) ──────────────────────────────────
        allowed_dirs = os.getenv("LOCAL_FILES_ALLOWED_DIRS", "")
        if allowed_dirs:
            dirs = [d.strip() for d in allowed_dirs.split(",") if d.strip()]
            servers["filesystem"] = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"] + dirs,
            }

        # ── Brave Search ──────────────────────────────────────────────────
        brave_key = os.getenv("BRAVE_SEARCH_API_KEY")
        if brave_key:
            servers["brave-search"] = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                "env": {"BRAVE_API_KEY": brave_key}
            }

        # ── Home Assistant ─────────────────────────────────────────────────
        ha_url   = os.getenv("HOME_ASSISTANT_URL")
        ha_token = os.getenv("HOME_ASSISTANT_TOKEN")
        if ha_url and ha_token:
            servers["home-assistant"] = {
                "command": "npx",
                "args": ["-y", "mcp-home-assistant"],
                "env": {
                    "HA_URL":   ha_url,
                    "HA_TOKEN": ha_token,
                }
            }

        # ── GitHub (opcional) ──────────────────────────────────────────────
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            servers["github"] = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": github_token}
            }

        return servers

    def list_active(self) -> list:
        return list(self.get_active_servers().keys())
