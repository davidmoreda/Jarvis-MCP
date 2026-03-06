# 🤖 Jarvis-MCP — Personal AI Assistant Server

Servidor MCP personal siempre activo con múltiples conectores, accesible remotamente via Tailscale VPN.

## Arquitectura

```
[Tú desde fuera via Tailscale] ──► [FastAPI :8000] ──► [Agent Core]
                                                               │
                                              [MCP Tool Connectors]
                                   ┌──────────┬──────────┬──────────┬──────────┐
                             Google Cal    Home      Ficheros   Web      Projects
                               /Gmail    Assistant   Locales   Search    + APIs
                                                               │
                                                      [Ollama container]
                                                     llama3.2 / mistral / qwen
```

## Stack

- **Backend**: FastAPI (OpenAI-compatible `/v1/chat/completions`)
- **Deploy**: Docker + Docker Compose — clonar y levantar
- **LLM Principal**: Ollama local en contenedor (100% gratis, sin tokens)
- **LLM Avanzado**: Claude API (opcional, para tareas complejas)
- **Conectores**: MCP modular — cada conector es un módulo independiente
- **Acceso remoto**: Tailscale VPN (seguro, sin exponer puertos)
- **Memoria**: SQLite persistente en volumen Docker

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

---

## 🚀 Quickstart — clonar y levantar

### Requisitos previos
- [Docker](https://docs.docker.com/get-docker/) instalado
- [Tailscale](https://tailscale.com/download) instalado en este PC y en tus dispositivos

### 1. Clonar el repo

```bash
git clone https://github.com/davidmoreda/Jarvis-MCP
cd Jarvis-MCP
```

### 2. Setup automático (recomendado)

```bash
bash setup.sh
```

El script hace todo: crea `.env` con API key aleatoria, te pregunta qué modelo Ollama quieres, construye las imágenes y levanta los contenedores. Al terminar te da el endpoint y la API key lista para usar.

### 2b. Setup manual (si prefieres)

```bash
cp .env.example .env
# Edita .env con tu API key y credenciales
docker compose up -d --build
```

### 3. Verificar que funciona

```bash
curl http://localhost:8000/health
# → {"status": "ok", "version": "0.1.0"}
```

### 4. Primera llamada

```bash
# Saca tu API key del .env
API_KEY=$(grep JARVIS_API_KEY .env | cut -d= -f2)

curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "jarvis", "messages": [{"role": "user", "content": "Hola Jarvis, ¿qué puedes hacer?"}]}'
```

---

## 🌐 Acceso desde fuera via Tailscale

Una vez que Jarvis está corriendo, puedes llamarlo desde cualquier dispositivo en tu red Tailscale:

```bash
curl http://<tailscale-ip-de-tu-pc>:8000/v1/chat/completions \
  -H "Authorization: Bearer TU_JARVIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jarvis",
    "messages": [{"role": "user", "content": "¿Qué tengo mañana en el calendario?"}]
  }'
```

Compatible con cualquier cliente OpenAI API: **Open WebUI**, **Continue.dev**, **Cursor**, apps móviles, etc.

---

## ⚙️ Gestión de contenedores

```bash
# Ver logs en tiempo real
docker compose logs -f jarvis

# Reiniciar solo la API (sin tocar Ollama)
docker compose restart jarvis

# Parar todo
docker compose down

# Parar y borrar datos (¡cuidado!)
docker compose down -v

# Actualizar (pull + rebuild)
git pull && docker compose up -d --build
```

---

## 🔑 Configuración de conectores

Edita `.env` para activar cada conector:

**Home Assistant:**
```
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=tu_long_lived_token
```

**Google Calendar / Gmail:**
1. Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com)
2. Activa Calendar API y Gmail API
3. Descarga `credentials.json` → cópialo en `credentials/google_credentials.json`
4. El primer uso abrirá el flujo OAuth automáticamente

**Brave Search** (opcional, mejores resultados que DuckDuckGo):
```
BRAVE_SEARCH_API_KEY=tu_key  # gratis hasta 2000 req/mes
```

**Claude API** (opcional, para razonamiento avanzado):
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 📁 Estructura del proyecto

```
Jarvis-MCP/
├── Dockerfile
├── docker-compose.yml
├── setup.sh                     # Wizard de primer arranque
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
│   └── jarvis.service           # systemd unit (alternativa a Docker)
├── credentials/                 # Google OAuth (gitignored)
├── data/                        # SQLite DBs (gitignored)
├── .env.example
└── requirements.txt
```
