# 🤖 Jarvis-MCP — Personal AI Assistant Server

Servidor MCP personal siempre activo con múltiples conectores, accesible remotamente via Tailscale VPN. Compatible con **macOS**, **Windows** y **Linux**.

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
- **Deploy**: Docker + Docker Compose — funciona en macOS, Windows y Linux
- **LLM Principal**: Ollama local en contenedor (100% gratis, sin tokens)
- **LLM Avanzado**: Claude API (opcional, para tareas complejas)
- **Conectores**: MCP modular — añade uno nuevo sin tocar el core
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

## 🚀 Quickstart

### Paso 0 — Requisitos previos

**Todos los sistemas:**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo
- [Git](https://git-scm.com/downloads)
- [Tailscale](https://tailscale.com/download) (para acceso remoto)

> En Windows: Docker Desktop requiere WSL 2. Al instalarlo te lo pide automáticamente.

---

### Paso 1 — Clonar el repo

```bash
git clone https://github.com/davidmoreda/Jarvis-MCP
cd Jarvis-MCP
```

---

### Paso 2 — Setup según tu sistema

#### 🍎 macOS
```bash
bash setup.sh
```

#### 🐧 Linux
```bash
bash setup.sh
```

#### 🪟 Windows (PowerShell)
```powershell
# Si es la primera vez, permite ejecutar scripts:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

.\setup.ps1
```

El script hace todo automáticamente: crea `.env` con API key segura, te pregunta qué modelo Ollama quieres, construye las imágenes y levanta los contenedores.

---

### Paso 3 — Verificar que funciona

#### macOS / Linux
```bash
curl http://localhost:8000/health
# → {"status": "ok", "version": "0.1.0"}
```

#### Windows (PowerShell)
```powershell
Invoke-RestMethod http://localhost:8000/health
```

---

### Paso 4 — Primera llamada a Jarvis

#### macOS / Linux
```bash
API_KEY=$(grep JARVIS_API_KEY .env | cut -d= -f2)

curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "jarvis", "messages": [{"role": "user", "content": "Hola Jarvis, ¿qué puedes hacer?"}]}'
```

#### Windows (PowerShell)
```powershell
$API_KEY = (Get-Content .env | Where-Object { $_ -match "^JARVIS_API_KEY=" }) -replace "^JARVIS_API_KEY=", ""
$headers = @{ "Authorization" = "Bearer $API_KEY"; "Content-Type" = "application/json" }
$body = '{"model":"jarvis","messages":[{"role":"user","content":"Hola Jarvis, ¿qué puedes hacer?"}]}'
Invoke-RestMethod http://localhost:8000/v1/chat/completions -Method POST -Headers $headers -Body $body
```

---

## 🌐 Acceso desde fuera via Tailscale

1. En el PC servidor: `tailscale up` (o abre la app de Tailscale)
2. Busca la IP de Tailscale de tu PC: `tailscale ip -4`
3. Desde cualquier dispositivo en tu red Tailscale:

```bash
curl http://<tailscale-ip>:8000/v1/chat/completions \
  -H "Authorization: Bearer TU_JARVIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "jarvis", "messages": [{"role": "user", "content": "¿Qué tengo mañana en el calendario?"}]}'
```

Compatible con cualquier cliente OpenAI API: **Open WebUI**, **Continue.dev**, **Cursor**, apps móviles, etc.

---

## ⚙️ Gestión de contenedores

Todos los comandos funcionan igual en macOS, Linux y Windows (PowerShell / Terminal):

```bash
# Ver logs en tiempo real
docker compose logs -f jarvis

# Reiniciar solo la API (sin tocar Ollama)
docker compose restart jarvis

# Parar todo
docker compose down

# Actualizar código (pull + rebuild)
git pull && docker compose up -d --build

# Parar y borrar TODOS los datos (¡cuidado!)
docker compose down -v
```

---

## 🔑 Configuración de conectores

Edita `.env` con cualquier editor de texto para activar cada conector:

**Home Assistant:**
```
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=tu_long_lived_token
```
El token se genera en Home Assistant → Perfil → Tokens de acceso de larga duración.

**Google Calendar / Gmail:**
1. Ve a [Google Cloud Console](https://console.cloud.google.com) → Nuevo proyecto
2. Activa las APIs: **Google Calendar API** y **Gmail API**
3. Crea credenciales OAuth 2.0 (tipo: aplicación de escritorio)
4. Descarga `credentials.json` y cópialo en `credentials/google_credentials.json`
5. La primera vez que Jarvis use Google te abrirá el navegador para autorizarlo

**Brave Search** (opcional, mejores resultados):
```
BRAVE_SEARCH_API_KEY=tu_key
```
Gratis hasta 2000 búsquedas/mes en [brave.com/search/api](https://brave.com/search/api/).

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
├── setup.sh                     # 🍎🐧 Setup para macOS / Linux
├── setup.ps1                    # 🪟 Setup para Windows (PowerShell)
├── src/
│   ├── main.py                  # FastAPI entry point
│   ├── agent/
│   │   ├── core.py              # Agent loop con tool calling
│   │   └── llm.py               # Cliente LLM (Ollama + Claude híbrido)
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
│   │   └── store.py             # Historial SQLite
│   └── auth/
│       └── middleware.py        # API Key auth
├── deploy/
│   └── jarvis.service           # systemd unit (Linux sin Docker)
├── credentials/                 # Google OAuth — gitignored
├── data/                        # SQLite DBs — gitignored
├── .env.example
└── requirements.txt
```
