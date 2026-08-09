# OSAP Auth Web — Integración bajo `/auth/*`

**Estado:** guía de integración (v1). No implementa todavía el reverse proxy definitivo.

---

# 1. Objetivo

Servir el frontend de OSAP Auth dentro de la aplicación principal OSAP bajo la ruta `/auth/*`,
**sin cambiar de subdominio** cuando el usuario gestiona su cuenta.

```
app.openmusicrepository.com
        │
        ├── /             → aplicación principal (osap-api web)
        │
        └── /auth/*       → OSAP Auth Web
                              │
                              └── OSAP Auth API
```

Así el usuario no "viaja" a otro dominio para gestionar su cuenta, pero la lógica de Auth no
se incrusta en cada aplicación OSAP.

---

# 2. Requisito de rutas relativas

El frontend de Auth usa **rutas absolutas** (`/auth/login`, `/auth/account`, …). Para servir
bajo un prefijo, el router debe montarse con `basename`. La aplicación se construye sin
hardcodear el subdominio: los enlaces son rutas internas (`/auth/...`), por lo que la
navegación permanece dentro del dominio actual.

Al integrar, se usa `BrowserRouter basename="/auth"` y las rutas de `App.tsx` pasan a ser
relativas al prefijo (p.ej. `login`, `register`, `account`), de modo que la ruta completa sea
`/auth/login`.

---

# 3. Esquema de integración

```
Host: app.openmusicrepository.com
  Apache / nginx:
    /            → SPA principal (app.openmusicrepository.com)
    /auth/*      → build de OSAP Auth Web (osap-auth/web/dist)
    /auth/api/*  → proxy → OSAP Auth API (https://auth.openmusicrepository.com)
```

El frontend de Auth llama a la API con `VITE_AUTH_API_URL`. En integración se configura para
que apunte al mismo origen bajo `/auth/api` (proxy) o directamente al servicio Auth según el
despliegue:

```env
# Ejemplo: proxy en el mismo host
VITE_AUTH_API_URL=/auth/api
```

---

# 4. Ejemplo Apache (referencia)

```apache
<VirtualHost *:443>
    ServerName app.openmusicrepository.com

    # Aplicación principal
    DocumentRoot "D:/.../osap-api/web/dist"

    # OSAP Auth Web bajo /auth
    Alias /auth "D:/.../osap-auth/web/dist"
    <Directory "D:/.../osap-auth/web/dist">
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
        RewriteEngine On
        # SPA fallback para /auth
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule ^/auth/ /auth/index.html [L]
    </Directory>

    # Proxy a la API de Auth (opcional, si no se usa subdominio dedicado)
    ProxyPass /auth/api/ https://auth.openmusicrepository.com/
    ProxyPassReverse /auth/api/ https://auth.openmusicrepository.com/
</VirtualHost>
```

---

# 5. Notas de integración

- La Auth Web se empaqueta en `osap-auth/web/dist` (build de Vite).
- No hay dependencia que impida servirla bajo `/auth`: no usa subdominios, cookies de dominio
  fijo ni rutas externas hardcodeadas.
- Los tokens se guardan en `localStorage` del origen actual; en integración el origen es
  `app.openmusicrepository.com`, por lo que la sesión es del dominio de la app principal
  (coherente con "no cambiar de subdominio").
- No se implementa el reverse proxy definitivo todavía; este documento es la guía de despliegue
  cuando se decida.

---
*Guía de integración de OSAP Auth Web (v1, 2026-08).*
