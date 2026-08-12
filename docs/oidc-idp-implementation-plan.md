# Plan: osap-auth como IdP OIDC (authorization code + PKCE) + pantallas embebidas

Estado de partida: los flujos OIDC descritos en `docs/social-login-and-oidc-v1.md` y
`docs/osap-api-oidc-integration-prompt-v1.md` están en DISEÑO, no implementados. El frontend
proxya la API bajo `/auth-api` (vite.config.ts) y el backend ya emite/valida JWKS y tokens de
usuario/servicio. Este plan implementa el lado **osap-auth** (IdP) para que osap-api actúe de
relying party, y añade el modo "embebido" (popup sin marca OSAP) en login y registro.

---

## 1. Contrato de endpoints (URLs a confirmar)

Valores públicos construidos con `public_base_url` + `public_path_prefix`:
- En **prod**: base `https://auth.openmusicrepository.com`, prefix `/auth-api`.
  - `authorization_endpoint = {base}{prefix}/auth/authorize`
  - `token_endpoint        = {base}{prefix}/oauth/token`
  - `jwks_uri              = {base}{prefix}/auth/.well-known/jwks.json`
  - `issuer                = https://auth.openmusicrepository.com`
- En **dev**: prefix vacío (la SPA proxya `/auth-api` → `127.0.0.1:8200`).

`redirect_uri` de osap-api: `https://api.openmusicrepository.com/auth/callback`
(se configura como `redirect_uris[0]` del cliente RP `osap-api`; confirmar con osap-api).

**Multi-origen / otras máquinas:** en producción `auth.openmusicrepository.com` es consumido por
otros servicios bajo `*.openmusicrepository.com` (p.ej. `api.openmusicrepository.com`) que pueden
residir en **otras máquinas**. Esto se resuelve sin cookies (sesión por bearer token, sin estado
cross-origin de cookies): el flujo OIDC usa navegación de nivel superior (`/auth/authorize` →
login embebido → redirect a la `redirect_uri` del RP) y `window.postMessage` en el popup
(mecanismo cross-origin que no requiere CORS), y el canje de tokens en `/oauth/token` es
server-to-server. Solo los fetch del navegador entre orígenes distintos necesitan CORS. Cada
servicio consume su propio `client_id`/`redirect_uris` registrado en `oauth_clients`.

---

## 2. Modelo de datos (nuevas tablas + columna)

- **`oauth_clients`** (clientes RP / relying parties). Entidad `OAuthClient`:
  - `id` uuid PK, `client_id` uuid único, `client_secret_hash`, `redirect_uris` (json),
    `grant_types` (json), `response_types` (json), `allowed_scopes` (json),
    `pkce_required` bool, `enabled` bool, `created_at`.
- **`authorization_codes`**. Entidad `AuthorizationCode` (opaco, hash, single-use, TTL corto):
  - `id` uuid PK, `client_id`, `user_id`, `redirect_uri`, `scope`, `nonce` (nullable),
    `code_challenge` (nullable), `code_challenge_method` (nullable), `code_hash`, `expires_at`,
    `used_at` (nullable), `created_at`.
- **`sessions`**: añadir columna `client_id` (uuid, nullable) para distinguir sesiones emitidas
  a un RP vía OIDC (aud del access token y validación en `refresh_token`).

Migrations: `0003_add_oauth_clients.py`, `0004_add_authorization_codes.py`,
`0005_add_session_client_id.py`.

---

## 3. Puertos / entidades / repos (dominio)

Nuevos:
- `domain/entities/oauth_client.py` — `OAuthClient` (+ `SCOPES`/validación de scope).
- `domain/entities/authorization_code.py` — `AuthorizationCode` (is_expired, mark_used, new).
- `domain/ports/oauth_client_repository.py` — `get_by_id`, `save`.
- `domain/ports/authorization_code_repository.py` — `get_by_hash`, `save`, `mark_used`.

Modificados:
- `domain/entities/session.py` — añadir `client_id: uuid.UUID | None`.
- `domain/ports/session_repository.py` — persistir `client_id` (los SQL ya usan `save`).

Helpers:
- `domain/util.py` — `pkce_challenge(verifier) -> str` = `base64url(sha256(verifier))` sin padding.
- `domain/ports/jwt.py` + `infrastructure/jwt/tokens.py` — `issue_access_token` acepta
  `audience: str | None = None` (default `self._audience`) y `nonce: str | None = None`
  (se añade como claim para anti-replay). Idem `_decode` ya valida `aud` recibido.

---

## 4. Casos de uso (application)

- `application/use_cases/oidc_authorize.py`
  - `ValidateAuthorizeRequestUseCase` — valida `client_id`/`redirect_uri`/`response_type=code`/
    `scope`/`pkce` contra el `OAuthClient`; si no autenticado devuelve la URL del SPA de login
    (embebido) con todos los parámetros. Devuelve payload validado (`AuthorizationRequest`).
  - `CompleteAuthorizationUseCase` — dado usuario autenticado + `AuthorizationRequest`: genera
    `AuthorizationCode` (hash), lo guarda y devuelve `redirect_uri + code + state`.
- `application/use_cases/oidc_token.py`
  - `ExchangeAuthorizationCodeUseCase` — valida code (single-use, TTL, PKCE con `code_verifier`,
    `client_secret`, `redirect_uri`), crea `Session(client_id=..., user_id=...)` con refresh,
    emite access token (`aud=client_id`, `token_use=user`, `nonce`) y devuelve
    `access_token + refresh_token + token_type + expires_in + scope`.
  - `RefreshTokenGrantUseCase` — para `grant_type=refresh_token`: valida refresh + `client_id`
    (sesión con ese client_id), rotación y reutilización (reutiliza patrón de `RefreshUseCase`),
    emite access token con `aud=client_id`.

---

## 5. Rutas API

- `api/routes/oidc.py` (nuevo):
  - `GET /.well-known/openid-configuration` — discovery OIDC (issuer, endpoints, grants,
    response_types, scopes, code_challenge_methods_supported, algs).
  - `GET /auth/authorize` — valida petición; si no hay sesión SPA redirige al login embebido;
    el SPA completa vía `POST /auth/authorize/complete`; si ya autenticado (bearer) completa
    directamente y responde `302` a `redirect_uri?code&state` (o 200 JSON con la URL).
  - `POST /auth/authorize/complete` — autenticado (bearer): crea el code y devuelve la URL.
- `api/routes/oauth.py` (modificar `/oauth/token`):
  - Soportar `grant_type=authorization_code` (PKCE) y `grant_type=refresh_token`
    (mantener `client_credentials`).
- `api/main.py` — incluir `oidc.router`.

---

## 6. Configuración y wiring

- `infrastructure/config.py` (`Settings`): `public_base_url`, `public_path_prefix`,
  `authorization_code_ttl_seconds` (p.ej. 300), `cors_origins` (lista de orígenes permitidos,
  p.ej. `["https://*.openmusicrepository.com", "https://api.openmusicrepository.com", ...]`).
  Cargar desde YAML/entorno.
- `api/main.py` / `application/context.py`: habilitar `CORSMiddleware` con `cors_origins`
  (necesario para fetch cross-origin del navegador desde `*.openmusicrepository.com`; el
  `Authorization` header y `X-Forwarded-*` ya los maneja el proxy). No exponer credenciales de
  cookie (`allow_credentials=False`).
- `application/context.py` (`AuthSettingsView`): añadir `public_base_url`, `public_path_prefix`,
  `authorization_code_ttl_seconds`. `AuthContext`: añadir
  `oauth_clients: OAuthClientRepository`, `authorization_codes: AuthorizationCodeRepository`.
- `infrastructure/container.py`: inyectar `SqlOAuthClientRepository` y
  `SqlAuthorizationCodeRepository` (JSON helpers igual que `SqlServiceClientRepository`).
- `infrastructure/cli.py`: comando `register-oauth-client` y seed de `osap-api`
  (redirect_uris=[osap-api callback], grants=[authorization_code, refresh_token],
  response_types=[code], allowed_scopes=[openid profile], pkce_required=true).

---

## 7. Frontend: modo embebido (ocultar marca OSAP)

- `web/src/components/AuthLayout.tsx` — prop `embedded: boolean`; cuando es true oculta
  `.brand` y muestra encabezado neutro ("Conectar con tu cuenta").
- `web/src/pages/Login/LoginPage.tsx` — detecta `?embed=1` (o `client_id` presente en la URL);
  renderiza embebido; al autenticar llama `authApi.completeAuthorization(payload)` con los
  parámetros OIDC de la URL + bearer; en éxito redirige a la `redirect_uri?code&state`
  (funciona en popup: el callback de osap-api postMessage al opener).
- `web/src/pages/Register/RegisterPage.tsx` — modo embebido (marca oculta); tras el registro
  muestra pantalla "revisa tu email" en estilo embebido (no completa OIDC hasta verificar+login).
- `web/src/api/authApi.ts` + `web/src/api/types.ts` — método `completeAuthorization`.

---

## 8. Seguridad

- PKCE obligatorio (S256) para clientes públicos; `osap-api` es confidencial (client_secret
  hasheado) y también `pkce_required=true`.
- Code de un solo uso (marcar `used_at`) y TTL corto.
- Validar `redirect_uri` exacta, `state` (CSRF) y `nonce` (anti-replay en el access token).
- `client_secret` solo en backend por entorno; nunca se devuelve al SPA.
- Rate limit en `authorize`, `complete`, `token` y en callbacks.
- **Origen/redirects**: `redirect_uri` siempre validada exacta contra `oauth_clients.redirect_uris`
  (nunca por prefijo) para evitar open-redirect en multi-origen. CORS solo para orígenes
  `*.openmusicrepository.com` configurados. Verificación de `Origin` en los fetch del SPA.

---

## 9. Tests

Backend (`tests/`):
- `tests/fakes.py`: `FakeOAuthClientRepository`, `FakeAuthorizationCodeRepository`;
  `make_context`/`make_settings_view` con los nuevos campos; `Session` con `client_id`.
- `tests/test_oidc.py` (nuevo):
  - well-known devuelve endpoints correctos (con/sin prefix).
  - authorize: valida client_id/redirect_uri/scope/pkce; rechaza cliente desconocido.
  - complete: genera code, redirige a redirect_uri con code+state.
  - token authorization_code: éxito (PKCE), code de un solo uso, redirect_uri/verifier erróneos,
    client_secret erróneo.
  - token refresh_token: rotación, reutilización detectada, aud=client_id.
- Correr `pytest` (y `python -m ruff` si está configurado en `pyproject.toml`).

Web (`web/`):
- `npm run typecheck` y `npm run lint`; ajustar tests de `AuthLayout` si existen.

---

## 10. Verificación end-to-end

1. Levantar backend (`python -m api.main` o uvicorn) y web (`npm run dev`).
2. `python -m infrastructure.cli register-oauth-client --client-id osap-api ...` (o seed).
3. `curl {base}/.well-known/openid-configuration` → endpoints con `/auth-api` en prod.
4. Flujo manual: abrir `{base}/auth/authorize?response_type=code&client_id=osap-api&
   redirect_uri=...&scope=openid%20profile&state=x&nonce=y&code_challenge=<S256>`, autenticarse
   en pantalla embebida (sin marca OSAP), recibir `code` en `redirect_uri`, canjear en
   `POST /oauth/token` (authorization_code + code_verifier) → access token de usuario
   (`aud=osap-api`, `token_use=user`) + refresh token; renovar con `grant_type=refresh_token`.
5. Verificar que ya no aparece "El inicio de sesión no está disponible temporalmente." desde
   osap-api (era el síntoma de que osap-auth aún no exponía estos endpoints).

---

## 11. Ficheros clave

Modificar: `domain/entities/session.py`, `domain/ports/jwt.py`, `infrastructure/jwt/tokens.py`,
`domain/util.py`, `api/routes/oauth.py`, `api/main.py`, `application/context.py`,
`infrastructure/config.py`, `infrastructure/container.py`, `infrastructure/cli.py`,
`tests/fakes.py`, `tests/conftest.py`, `web/src/components/AuthLayout.tsx`,
`web/src/pages/Login/LoginPage.tsx`, `web/src/pages/Register/RegisterPage.tsx`,
`web/src/api/authApi.ts`, `web/src/api/types.ts`, `docs/social-login-and-oidc-v1.md`.

Crear: `domain/entities/oauth_client.py`, `domain/entities/authorization_code.py`,
`domain/ports/oauth_client_repository.py`, `domain/ports/authorization_code_repository.py`,
`infrastructure/repositories/sql_oauth_client_repository.py`,
`infrastructure/repositories/sql_authorization_code_repository.py`,
`infrastructure/migrations/versions/0003_add_oauth_clients.py`,
`infrastructure/migrations/versions/0004_add_authorization_codes.py`,
`infrastructure/migrations/versions/0005_add_session_client_id.py`,
`application/use_cases/oidc_authorize.py`, `application/use_cases/oidc_token.py`,
`api/routes/oidc.py`, `tests/test_oidc.py`.
