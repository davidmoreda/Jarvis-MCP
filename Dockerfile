FROM python:3.11-slim

WORKDIR /app

# ── Sistema base ───────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# ── Node.js 20 LTS (necesario para claude CLI y servidores MCP npm) ────────
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── Claude Code CLI (@anthropic-ai/claude-code) ───────────────────────────
# Este es el CLI que usa el Claude Agent SDK como backend
RUN npm install -g @anthropic-ai/claude-code

# ── Python deps ───────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Código fuente ──────────────────────────────────────────────────────────
COPY src/ ./src/

# ── Directorios persistentes ───────────────────────────────────────────────
RUN mkdir -p data credentials

# ── Config claude CLI ──────────────────────────────────────────────────────
# El directorio ~/.claude persiste el login OAuth entre reinicios
# Se monta como volumen en docker-compose.yml
ENV CLAUDE_CONFIG_DIR=/root/.claude

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
