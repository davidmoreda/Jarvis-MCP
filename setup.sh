#!/usr/bin/env bash
# setup.sh — Primer arranque de Jarvis-MCP
# Uso: bash setup.sh
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🤖 Jarvis-MCP Setup${NC}"
echo "────────────────────────────────────────"

# 1. Comprobar dependencias
command -v docker >/dev/null 2>&1 || { echo "❌ Docker no está instalado. https://docs.docker.com/get-docker/"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "❌ Docker Compose no está instalado."; exit 1; }

# 2. Crear .env si no existe
if [ ! -f .env ]; then
  cp .env.example .env
  # Generar API key aleatoria
  API_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
  sed -i "s/change-me-to-a-strong-secret/${API_KEY}/" .env
  echo -e "${GREEN}✅ .env creado con API key aleatoria${NC}"
  echo -e "${YELLOW}⚠️  Edita .env para añadir tus credenciales (Home Assistant, Google, etc.)${NC}"
else
  echo "✅ .env ya existe, no se sobreescribe"
fi

# 3. Crear directorio de credenciales
mkdir -p credentials data

# 4. Preguntar modelo Ollama
echo ""
echo "¿Qué modelo Ollama quieres usar?"
echo "  1) llama3.2        (recomendado, 2GB)"
echo "  2) llama3.3        (mejor calidad, 5GB)"
echo "  3) mistral         (rápido, 4GB)"
echo "  4) qwen2.5         (muy bueno, 4GB)"
echo "  5) Otro (introduce el nombre)"
read -p "Opción [1]: " MODEL_CHOICE
MODEL_CHOICE=${MODEL_CHOICE:-1}

case $MODEL_CHOICE in
  1) MODEL="llama3.2" ;;
  2) MODEL="llama3.3" ;;
  3) MODEL="mistral" ;;
  4) MODEL="qwen2.5" ;;
  5) read -p "Nombre del modelo: " MODEL ;;
  *) MODEL="llama3.2" ;;
esac

# Actualizar .env con el modelo elegido
sed -i "s/^OLLAMA_MODEL=.*/OLLAMA_MODEL=${MODEL}/" .env
echo -e "${GREEN}✅ Modelo configurado: ${MODEL}${NC}"

# 5. Levantar servicios
echo ""
echo -e "${GREEN}🚀 Levantando Jarvis con Docker Compose...${NC}"
docker compose up -d --build

# 6. Esperar a que Jarvis esté listo
echo "⏳ Esperando a que la API arranque..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# 7. Test rápido
echo ""
API_KEY=$(grep JARVIS_API_KEY .env | cut -d= -f2)
HEALTH=$(curl -sf http://localhost:8000/health)

echo -e "${GREEN}────────────────────────────────────────${NC}"
echo -e "${GREEN}✅ Jarvis está activo!${NC}"
echo ""
echo "📡 Endpoint: http://localhost:8000"
echo "🔑 Tu API Key: ${API_KEY}"
echo ""
echo "Test rápido:"
echo "  curl http://localhost:8000/v1/chat/completions \\"
echo "    -H 'Authorization: Bearer ${API_KEY}' \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"model\": \"jarvis\", \"messages\": [{\"role\": \"user\", \"content\": \"Hola Jarvis!\"}]}'"
echo ""
echo -e "${YELLOW}Logs: docker compose logs -f jarvis${NC}"
echo -e "${YELLOW}Parar: docker compose down${NC}"
