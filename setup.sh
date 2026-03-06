#!/usr/bin/env bash
# setup.sh — Primer arranque de Jarvis-MCP
# Compatible: macOS y Linux
# Uso: bash setup.sh
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🤖 Jarvis-MCP Setup${NC}"
echo "────────────────────────────────────────"

# Detectar OS
OS="$(uname -s)"
case "$OS" in
  Darwin) PLATFORM="macOS" ;;
  Linux)  PLATFORM="Linux" ;;
  *)      PLATFORM="Unknown" ;;
esac
echo "📦 Plataforma detectada: $PLATFORM"

# 1. Comprobar dependencias
command -v docker >/dev/null 2>&1 || {
  echo -e "${RED}❌ Docker no está instalado.${NC}"
  if [ "$PLATFORM" = "macOS" ]; then
    echo "   Instala Docker Desktop: https://www.docker.com/products/docker-desktop/"
  else
    echo "   Instala Docker: https://docs.docker.com/get-docker/"
  fi
  exit 1
}

docker compose version >/dev/null 2>&1 || docker-compose version >/dev/null 2>&1 || {
  echo -e "${RED}❌ Docker Compose no está disponible.${NC}"
  exit 1
}

# Detectar si usar "docker compose" o "docker-compose"
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
else
  DC="docker-compose"
fi

# 2. Crear .env si no existe
if [ ! -f .env ]; then
  cp .env.example .env

  # Generar API key aleatoria (compatible macOS y Linux)
  API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null \
    || openssl rand -hex 32 2>/dev/null \
    || LC_ALL=C tr -dc 'a-f0-9' < /dev/urandom | head -c 64)

  # sed -i compatible macOS (requiere '') y Linux (no requiere '')
  if [ "$PLATFORM" = "macOS" ]; then
    sed -i '' "s/change-me-to-a-strong-secret/${API_KEY}/" .env
  else
    sed -i "s/change-me-to-a-strong-secret/${API_KEY}/" .env
  fi

  echo -e "${GREEN}✅ .env creado con API key aleatoria${NC}"
  echo -e "${YELLOW}⚠️  Edita .env para añadir tus credenciales (Home Assistant, Google, etc.)${NC}"
else
  echo "✅ .env ya existe, no se sobreescribe"
fi

# 3. Crear directorios necesarios
mkdir -p credentials data

# 4. Elegir modelo Ollama
echo ""
echo "¿Qué modelo Ollama quieres usar?"
echo "  1) llama3.2     (recomendado — 2GB, rápido)"
echo "  2) llama3.3     (mejor calidad — 5GB)"
echo "  3) mistral      (muy rápido — 4GB)"
echo "  4) qwen2.5      (excelente razonamiento — 4GB)"
echo "  5) otro         (introduce el nombre manualmente)"
read -p "Opción [1]: " MODEL_CHOICE
MODEL_CHOICE=${MODEL_CHOICE:-1}

case $MODEL_CHOICE in
  1) MODEL="llama3.2" ;;
  2) MODEL="llama3.3" ;;
  3) MODEL="mistral" ;;
  4) MODEL="qwen2.5" ;;
  5) read -p "Nombre del modelo Ollama: " MODEL ;;
  *) MODEL="llama3.2" ;;
esac

if [ "$PLATFORM" = "macOS" ]; then
  sed -i '' "s/^OLLAMA_MODEL=.*/OLLAMA_MODEL=${MODEL}/" .env
else
  sed -i "s/^OLLAMA_MODEL=.*/OLLAMA_MODEL=${MODEL}/" .env
fi
echo -e "${GREEN}✅ Modelo configurado: ${MODEL}${NC}"

# 5. Levantar servicios
echo ""
echo -e "${GREEN}🚀 Construyendo y levantando Jarvis...${NC}"
$DC up -d --build

# 6. Esperar a que Jarvis esté listo (máx 60s)
echo "⏳ Esperando a que la API arranque..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# 7. Resultado
echo ""
API_KEY=$(grep JARVIS_API_KEY .env | cut -d= -f2)

echo -e "${GREEN}────────────────────────────────────────${NC}"
echo -e "${GREEN}✅ ¡Jarvis está activo!${NC}"
echo ""
echo "📡 Endpoint local:   http://localhost:8000"
echo "🔑 Tu API Key:       ${API_KEY}"
echo ""
echo "Test rápido:"
echo "  curl http://localhost:8000/v1/chat/completions \\"
echo "    -H 'Authorization: Bearer ${API_KEY}' \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"model\": \"jarvis\", \"messages\": [{\"role\": \"user\", \"content\": \"Hola Jarvis!\"}]}'"
echo ""
echo -e "${YELLOW}Ver logs:   $DC logs -f jarvis${NC}"
echo -e "${YELLOW}Parar:      $DC down${NC}"
echo -e "${YELLOW}Reiniciar:  $DC restart jarvis${NC}"
