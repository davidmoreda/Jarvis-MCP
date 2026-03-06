"""
Base class para todos los conectores MCP de Jarvis.
Cada conector implementa get_tools() y call_tool().
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseConnector(ABC):

    @abstractmethod
    def get_tools(self) -> List[Dict]:
        """
        Devuelve la lista de herramientas en formato OpenAI tool spec.
        [
          {
            "type": "function",
            "function": {
              "name": "...",
              "description": "...",
              "parameters": { ... JSON Schema ... }
            }
          }
        ]
        """
        ...

    @abstractmethod
    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Ejecuta la herramienta con los argumentos dados y devuelve el resultado."""
        ...
