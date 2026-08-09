# OSAP Auth — Documentación de despliegue (v1.0)

**Requisitos:** Python 3.11+, MySQL 8, Apache/XAMPP (opcional, para servir bajo host local).

---

# 1. Preparar el entorno

```powershell
cd D:\Proyectos\AI_OSAP\osap-auth
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

# 2. Crear la base de datos

```sql
CREATE DATABASE osap_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'osap_auth'@'localhost' IDENTIFIED BY '<clave>';
GRANT ALL PRIVILEGES ON osap_auth.* TO 'osap_auth'@'localhost';
FLUSH PRIVILEGES;
```

# 3. Configurar secretos

```powershell
# Generar claves
.\.venv\Scripts\python -m infrastructure.crypto.keygen
```

Copia `config.example.yaml` a `config.yaml` y `env.example` a `.env`, y rellena:
- `OSAP_AUTH_DB_*`
- `OSAP_AUTH_EMAIL_PEPPER`, `OSAP_AUTH_EMAIL_AEAD_KEY`, `OSAP_AUTH_TOKEN_PEPPER`
- `OSAP_AUTH_JWT_PRIVATE_KEY`, `OSAP_AUTH_JWT_PUBLIC_KEY` (los PEM con `\n` escapado)
- `OSAP_AUTH_ISSUER`, `OSAP_AUTH_AUDIENCE`

> Las claves **nunca** se commitean. Usa el gestor de secretos de tu entorno.

# 4. Migraciones

```powershell
$env:OSAP_AUTH_DB_PASSWORD="<clave>"
.\.venv\Scripts\python -m infrastructure.cli migrate
```

# 5. Crear clientes de servicio

```powershell
.\.venv\Scripts\python -m infrastructure.cli create-client --scopes storage:read,api:read
```

Guarda el `client_id`/`client_secret` devueltos (el secreto solo se muestra una vez).

# 6. Arrancar el servicio

```powershell
.\.venv\Scripts\python -m uvicorn api.main:create_app_from_settings --factory --host 127.0.0.1 --port 8200
```

Verificación: `http://127.0.0.1:8200/health` → `{"status":"ok"}`.

# 7. Apache (opcional)

VirtualHost de ejemplo en `httpd-vhosts.conf` (hosts: `127.0.0.1 osap-auth`):

```
<VirtualHost *:80>
    ServerName osap-auth
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8200/
    ProxyPassReverse / http://127.0.0.1:8200/
    ErrorLog "logs/osap-auth-error.log"
    CustomLog "logs/osap-auth-access.log" combined
</VirtualHost>
```

# 8. Tests

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m mypy .
.\.venv\Scripts\python -m pytest
```

---
*Documentación de despliegue de osap-auth v1.0 (2026-08).*
