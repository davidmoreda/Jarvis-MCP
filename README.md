# 🤖 Jarvis-MCP — Personal AI Assistant Server

Servidor MCP personal siempre activo con múltiples conectores, accesible remotamente via Tailscale VPN.

## Arquitectura

```
[Tú desde fuera via Tailscale] ──► [FastAPI Server :8000] ──► [Agent Core]
                                                                      │
                                                         [MCP Tool Connectors]
                                              ┌───────────┬───────────┬──────────┬──────────┐
                                        Google Cal    Home      Ficheros   Web      Projects
                                          /Gmail    Assistant   Locales   Search    + APIs
```

## Stack

- **Backend**: FastAPI (OpenAI-compatible `/v1/chat/completions`)
- **LLM Principal**: Ollama local (llama3, mistral, qwen...) — 100% gratis, sin tokens
- **LLM Avanzado**: Claude API (opcional, para tareas complejas)
- **Conectores**: MCP modular — cada conector es un módulo independiente
- **Acceso remoto**: Tailscale VPN (seguro, sin exponer puertos)
- **Persistencia**: systemd service (siempre activo tras reinicios)
- **Memoria**: SQLite para historial de conversaciones

## Conectores disponibles

| Conector | Estado | Descripción |
|---|---|---|
| `google_calendar` | 🔧 WIP | Leer/crear/modificar eventos |
| `gmail` | 🔧 WIP | Leer/enviar/buscar emails |
| `home_assistant` | 🔧 WIP | Control domótica (luces, sensores, escenas) |
| `local_files` | 🔧 WIP | Leer/escribir ficheros del sistema |
| `web_search` | 🔧 WIP | Búsqueda web (DuckDuckGo/Brave API) |
| `projects` | 🔧 WIP | Gestión de proyectos, notas, brainstorming |
| `api_connector` | 🔧 WIP | Conector genérico a APIs externas |

## Quickstart

```bash
# 1. Clonar y configurar
git clone https://github.com/davidmoreda/Jarvis-MCP
cd Jarvis-MCP
cp .env.example .env
# Edita .env con tus credenciales

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2

# 4. Ejecutar en desarrollo
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Instalar como servicio (siempre activo)
sudo cp deploy/jarvis.service /etc/systemd/system/
sudo systemctl enable --now jarvis
```

## Acceso desde fuera via Tailscale

```bash
# Desde cualquier dispositivo en tu red Tailscale
curl http://<tailscale-ip>:8000/v1/chat/completions \
  -H "Authorization: Bearer TU_JARVIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jarvis",
    "messages": [{"role": "user", "content": "¿Qué tengo mañana en el calendario?"}]
  }'
```

Compatible con cualquier cliente que soporte OpenAI API (Open WebUI, Continue.dev, etc.)

## Estructura del proyecto

```
Jarvis-MCP/
├── src/
│   ├── main.py                  # FastAPI entry point
│   ├── agent/
│   │   ├── core.py              # Agent loop (tool calling)
│   │   └── llm.py               # Abstracción LLM (Ollama + Claude)
│   ├── connectors/
│   │   ├── base.py              # Clase base MCP connector
│   │   ├── google_calendar.py
│   │   ├── gmail.py
│   │   ├── home_assistant.py
│   │   ├── local_files.py
│   │   ├── web_search.py
│   │   ├── projects.py
│   │   └── api_connector.py
│   ├── memory/
│   │   └── store.py             # SQLite conversation memory
│   └── auth/
│       └── middleware.py        # API Key auth
├── deploy/
│   └── jarvis.service           # systemd unit file
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```
