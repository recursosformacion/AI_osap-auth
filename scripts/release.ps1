<#
.SYNOPSIS
    Libera una versión de osap-auth a producción (91.134.255.134).

.DESCRIPTION
    - Ejecuta tests/lint/tipos del backend.
    - Construye el frontend (web/) con el entorno de producción.
    - Sube el código del backend y crea/actualiza el venv.
    - Despliega config.production.yaml como config.yaml en el servidor.
    - Ejecuta las migraciones.
    - Sube el build del frontend (web/dist).
    - Aprovisiona (idempotente) el servicio systemd, el sitio nginx y el certificado
      autofirmado del origen si no existen.
    - Reinicia el servicio y verifica /health.

.NOTES
    - config.yaml (dev) y config.production.yaml NO se suben al repo.
    - Producción solo se toca al cerrar una versión.
    - Requiere `ssh` con clave configurada para ocw@91.134.255.134.
#>
param(
    [string]$Server = "91.134.255.134",
    [string]$User = "ocw",
    [string]$RemoteDir = "/home/ocw/openmusicrepository.com/osap-auth",
    [string]$Domain = "auth.openmusicrepository.com",
    [switch]$SkipTests,
    [switch]$SkipMigrations,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot | Split-Path -Parent

function Invoke-Remote($cmd) {
    ssh -o BatchMode=yes "$User@$Server" $cmd
    if ($LASTEXITCODE -ne 0) { throw "Fallo remoto: $cmd" }
}

Write-Host "== Liberación de osap-auth ==" -ForegroundColor Cyan

if (-not $SkipTests) {
    Write-Host "[1/8] Tests, lint y tipos (backend)..."
    & "$root\.venv\Scripts\python.exe" -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Tests fallidos" }
    & "$root\.venv\Scripts\ruff.exe" check .
    if ($LASTEXITCODE -ne 0) { throw "Lint fallido" }
    & "$root\.venv\Scripts\mypy.exe" api application domain infrastructure
    if ($LASTEXITCODE -ne 0) { throw "Mypy fallido" }
} else {
    Write-Host "[1/8] Tests omitidos"
}

Write-Host "[2/8] Comprobando config.production.yaml..."
$prodConfig = Join-Path $root "config.production.yaml"
if (-not (Test-Path $prodConfig)) { throw "No existe config.production.yaml" }

Write-Host "[3/8] Subiendo código del backend al servidor..."
Invoke-Remote "mkdir -p $RemoteDir"
tar.exe -czf - `
    --exclude=.venv --exclude=.git --exclude=.pytest_cache --exclude=.ruff_cache `
    --exclude=.mypy_cache --exclude=__pycache__ --exclude=.env --exclude=config.yaml `
    --exclude=config.production.yaml --exclude=web --exclude=*.egg-info `
    -C $root . |
    ssh -o BatchMode=yes "$User@$Server" "tar -xzf - -C $RemoteDir"
if ($LASTEXITCODE -ne 0) { throw "Fallo al subir el backend" }

Write-Host "[4/8] Preparando venv en el servidor (si no existe)..."
Invoke-Remote "cd $RemoteDir && (test -x .venv/bin/python || python3 -m venv .venv) && ./.venv/bin/pip install -e '.[dev]' -q"

Write-Host "[5/8] Desplegando config.production.yaml como config.yaml..."
scp -o BatchMode=yes $prodConfig "${User}@${Server}:/tmp/config.production.yaml"
if ($LASTEXITCODE -ne 0) { throw "Fallo al subir la configuración" }
Invoke-Remote "cp /tmp/config.production.yaml $RemoteDir/config.yaml && rm -f /tmp/config.production.yaml"

if (-not $SkipMigrations) {
    Write-Host "[6/8] Ejecutando migraciones..."
    Invoke-Remote "cd $RemoteDir && ./.venv/bin/python -m infrastructure.cli migrate"
} else {
    Write-Host "[6/8] Migraciones omitidas"
}

if (-not $SkipFrontend) {
    Write-Host "[7/8] Construyendo frontend de producción y subiéndolo..."
    Push-Location (Join-Path $root "web")
    & "node" "node_modules/vite/bin/vite.js" build
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Build de frontend fallido" }
    Pop-Location
    $webDist = Join-Path $root "web\dist"
    Invoke-Remote "mkdir -p $RemoteDir/web/dist"
    tar.exe -czf - -C $webDist . |
        ssh -o BatchMode=yes "$User@$Server" "tar -xzf - -C $RemoteDir/web/dist"
    if ($LASTEXITCODE -ne 0) { throw "Fallo al subir el frontend" }
} else {
    Write-Host "[7/8] Frontend omitido"
}

Write-Host "[8/8] Aprovisionando servicio y sitio, reiniciando y verificando..."
# Servicio systemd (idempotente)
scp -o BatchMode=yes (Join-Path $PSScriptRoot "osap-auth.service") "${User}@${Server}:/tmp/osap-auth.service" | Out-Null
Invoke-Remote "sudo cp /tmp/osap-auth.service /etc/systemd/system/osap-auth.service && sudo systemctl daemon-reload && sudo systemctl enable osap-auth >/dev/null 2>&1 || true"

# Sitio nginx (idempotente) + certificado autofirmado del origen si no existe
scp -o BatchMode=yes (Join-Path $PSScriptRoot "auth.openmusicrepository.com.conf") "${User}@${Server}:/tmp/auth.conf" | Out-Null
Invoke-Remote "sudo mkdir -p /etc/nginx/ssl/$Domain && (test -f /etc/nginx/ssl/$Domain/fullchain.cer || sudo openssl req -x509 -nodes -newkey rsa:2048 -days 3650 -keyout /etc/nginx/ssl/$Domain/private.key -out /etc/nginx/ssl/$Domain/fullchain.cer -subj '/CN=$Domain' -addext 'subjectAltName=DNS:$Domain' >/dev/null 2>&1) && sudo cp /tmp/auth.conf /etc/nginx/sites-enabled/$Domain.conf && sudo rm -f /tmp/auth.conf /tmp/osap-auth.service"

Invoke-Remote "sudo systemctl restart osap-auth && sudo nginx -t >/dev/null 2>&1 && sudo nginx -s reload && sleep 4 && curl -s http://127.0.0.1:8200/health"

Write-Host "Liberación completada. Web: https://$Domain" -ForegroundColor Green
