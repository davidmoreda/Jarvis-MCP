"""
Conector Web Search — búsqueda web via DuckDuckGo (sin API key)
o Brave Search API (con API key, más resultados).
"""
import os
from typing import List, Dict, Any
import httpx

from src.connectors.base import BaseConnector

BRAVE_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "")


class WebSearchConnector(BaseConnector):

    def get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Busca información actualizada en internet.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Consulta de búsqueda"},
                            "num_results": {"type": "integer", "description": "Número de resultados (default: 5)", "default": 5}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        query = args["query"]
        num = args.get("num_results", 5)

        if BRAVE_API_KEY:
            return await self._brave_search(query, num)
        return await self._ddg_search(query, num)

    async def _brave_search(self, query: str, num: int) -> List[Dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY},
                params={"q": query, "count": num}
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("web", {}).get("results", [])
            return [{"title": r["title"], "url": r["url"], "snippet": r.get("description", "")} for r in results]

    async def _ddg_search(self, query: str, num: int) -> List[Dict]:
        """DuckDuckGo Instant Answer API (sin API key, resultados limitados)."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", ""),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data.get("AbstractText", "")
                })
            for r in data.get("RelatedTopics", [])[:num]:
                if "Text" in r:
                    results.append({
                        "title": r.get("Text", "")[:80],
                        "url": r.get("FirstURL", ""),
                        "snippet": r.get("Text", "")
                    })
            return results[:num]
