# setup.ps1 — Primer arranque de Jarvis-MCP en Windows
# Uso: .\setup.ps1
# Requiere: PowerShell 5+ y Docker Desktop instalado

$ErrorActionPreference = "Stop"

Write-Host "🤖 Jarvis-MCP Setup (Windows)" -ForegroundColor Green
Write-Host "────────────────────────────────────────"

# 1. Comprobar Docker
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker no está corriendo. Abre Docker Desktop primero." -ForegroundColor Red
    Write-Host "   Descarga: https://www.docker.com/products/docker-desktop/"
    exit 1
}

# Detectar si usar "docker compose" o "docker-compose"
$DC = "docker compose"
try {
    docker compose version | Out-Null
} catch {
    $DC = "docker-compose"
}

Write-Host "✅ Docker detectado. Usando: $DC"

# 2. Crear .env si no existe
if (-Not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"

    # Generar API key aleatoria
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $API_KEY = -join ($bytes | ForEach-Object { $_.ToString("x2") })

    # Reemplazar placeholder en .env
    (Get-Content ".env") -replace "change-me-to-a-strong-secret", $API_KEY | Set-Content ".env"

    Write-Host "✅ .env creado con API key aleatoria" -ForegroundColor Green
    Write-Host "⚠️  Edita .env para añadir tus credenciales (Home Assistant, Google, etc.)" -ForegroundColor Yellow
} else {
    Write-Host "✅ .env ya existe, no se sobreescribe"
}

# 3. Crear directorios necesarios
New-Item -ItemType Directory -Force -Path "credentials" | Out-Null
New-Item -ItemType Directory -Force -Path "data" | Out-Null

# 4. Elegir modelo Ollama
Write-Host ""
Write-Host "¿Qué modelo Ollama quieres usar?"
Write-Host "  1) llama3.2     (recomendado — 2GB, rápido)"
Write-Host "  2) llama3.3     (mejor calidad — 5GB)"
Write-Host "  3) mistral      (muy rápido — 4GB)"
Write-Host "  4) qwen2.5      (excelente razonamiento — 4GB)"
Write-Host "  5) otro         (introduce el nombre manualmente)"
$MODEL_CHOICE = Read-Host "Opción [1]"
if ([string]::IsNullOrEmpty($MODEL_CHOICE)) { $MODEL_CHOICE = "1" }

switch ($MODEL_CHOICE) {
    "1" { $MODEL = "llama3.2" }
    "2" { $MODEL = "llama3.3" }
    "3" { $MODEL = "mistral" }
    "4" { $MODEL = "qwen2.5" }
    "5" { $MODEL = Read-Host "Nombre del modelo Ollama" }
    default { $MODEL = "llama3.2" }
}

(Get-Content ".env") -replace "^OLLAMA_MODEL=.*", "OLLAMA_MODEL=$MODEL" | Set-Content ".env"
Write-Host "✅ Modelo configurado: $MODEL" -ForegroundColor Green

# 5. Levantar servicios
Write-Host ""
Write-Host "🚀 Construyendo y levantando Jarvis..." -ForegroundColor Green
Invoke-Expression "$DC up -d --build"

# 6. Esperar a que Jarvis esté listo (máx 60s)
Write-Host "⏳ Esperando a que la API arranque..."
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
}

# 7. Resultado
$API_KEY = (Get-Content ".env" | Where-Object { $_ -match "^JARVIS_API_KEY=" }) -replace "^JARVIS_API_KEY=", ""

Write-Host ""
Write-Host "────────────────────────────────────────" -ForegroundColor Green
if ($ready) {
    Write-Host "✅ ¡Jarvis está activo!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Jarvis puede estar aún arrancando. Comprueba: docker compose logs jarvis" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "📡 Endpoint local:   http://localhost:8000"
Write-Host "🔑 Tu API Key:       $API_KEY"
Write-Host ""
Write-Host "Test rápido (pega esto en PowerShell):"
Write-Host @"
`$headers = @{ "Authorization" = "Bearer $API_KEY"; "Content-Type" = "application/json" }
`$body = '{"model":"jarvis","messages":[{"role":"user","content":"Hola Jarvis!"}]}'
Invoke-RestMethod http://localhost:8000/v1/chat/completions -Method POST -Headers `$headers -Body `$body
"@
Write-Host ""
Write-Host "Ver logs:   $DC logs -f jarvis" -ForegroundColor Yellow
Write-Host "Parar:      $DC down" -ForegroundColor Yellow
Write-Host "Reiniciar:  $DC restart jarvis" -ForegroundColor Yellow
