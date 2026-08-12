# osap-auth — Diseño: Login social (OIDC upstream) + osap-auth como IdP (OIDC downstream)

**Estado:** v1 IMPLEMENTADO (2026-08) en el lado IdP (osap-auth). Se implementó el flujo
Authorization Code + PKCE, discovery OIDC, registro de clientes RP, pantallas embebidas y el
**login social (upstream)** para Google y GitHub (tabla `provider_accounts`, endpoints
`/auth/oauth/{provider}` y `/auth/oauth/{provider}/callback`, validación de `redirect_uri` por
dominio). Contrato congelado `osap-auth-api-v1.0.md`; contrato interno independiente de
osap-api/osap-storage.

---

## 1. Objetivo y principio rector

- osap-api **invoca el logon** pero no gestiona credenciales: el flujo ideal es que **osap-auth
  sea el Identity Provider (IdP) hosteado** y muestre **su** pantalla de login.
- osap-api solo: (a) redirige el navegador a osap-auth, y (b) canjea el código resultante.
- Esto da una única identidad y una única pantalla, con menos superficie de ataque en osap-api.

Dos direcciones:

- **Upstream (social):** osap-auth autentica al usuario vía proveedores externos
  (Google, GitHub, …) mediante OAuth2/OIDC *authorization_code* + PKCE.
- **Downstream (a osap-api):** osap-auth actúa de IdP OIDC; osap-api es un *relying party*
  que recibe tokens de **usuario**.

---

## 2. osap-auth como IdP OIDC (flujo Authorization Code + PKCE)

1. El usuario pulsa *Login* en osap-api.
2. osap-api construye y redirige a:

   ```
   https://auth.openmusicrepository.com/auth/authorize
     ?response_type=code
     &client_id=osap-api
     &redirect_uri=https://api.openmusicrepository.com/auth/callback
     &scope=openid profile
     &state=<csrf>
     &nonce=<anti-replay>
     &code_challenge=<base64url(sha256(verifier))>
   ```

3. osap-auth muestra su pantalla de login (email/password o "Continuar con Google/GitHub").
4. Autenticado, osap-auth redirige a la `redirect_uri` de osap-api con `?code=...&state=...`.
5. osap-api canjea el code en `POST /oauth/token` con `grant_type=authorization_code` +
   `code_verifier` (PKCE) → access token (usuario) + refresh token.

### Piezas a añadir en osap-auth
- `/.well-known/openid-configuration` (discovery OIDC). JWKS ya existe.
- `/auth/authorize` (authorization_code + PKCE + `state`/`nonce`).
- Ampliar `/oauth/token` para `grant_type=authorization_code` (hoy solo `client_credentials`).
- Registrar osap-api como **cliente RP**: `redirect_uris`, `grant_types`, `response_types`,
  scopes permitidos, `pkce_required`.

---

## 3. Login social (upstream)

- Nueva tabla `provider_accounts` → `(provider, provider_sub, user_id, email, name, linked_at)`.
- Endpoints `/auth/oauth/{provider}` (inicio) y `/auth/oauth/{provider}/callback`, con PKCE + `state`.
- Al volver del proveedor:
  - email ya existe → **vincular** a esa cuenta;
  - no existe → **crear** cuenta (según política de `email_verified`).
- `email_verified` por proveedor: **Google lo entrega; GitHub no**. Decisión abierta:
  confiar en el proveedor o exigir verificación propia.
- El `state` transporta el `return_to`/contexto de osap-api para no perder el flujo.

---

## 4. Consumo por osap-api

- osap-api **no** toca credenciales ni pantalla de login: **usa la pantalla de osap-auth**.
- Tokens recibidos:
  - **Access token de usuario:** `sub=user_id`, `token_use="user"`, `aud=osap-api` → lo usa
    contra su propio backend.
  - **Refresh token:** renovar sin re-redirigir (rotación).
  - `id_token` (opcional): `iss/sub/aud/nonce/email_verified`.
- Distinción crítica para osap-api:
  - token de **usuario** → `sub=user_id`, `token_use=user` (APIs de usuario);
  - token de **servicio** → `sub=client_id`, `token_use=service` (machine-to-machine, osap-storage).

---

## 5. Modelo de datos

- `provider_accounts` (nueva).
- Clientes RP: **reutilizar/ampliar `service_clients`** (añadir `redirect_uris`,
  `grant_types`, `response_types`, `allowed_scopes`, `pkce_required`) **o** nueva tabla
  `oauth_clients`. Decisión abierta; reutilizar `service_clients` evita tabla nueva y ya existe
  el `client_id` de osap-api.
- `authorization_codes`: opacos, hasheados, single-use, TTL corto (puede reutilizarse `tokens`).
- Las `sessions` existentes cubren la sesión; el code apunta a una sesión.

---

## 6. Seguridad

- PKCE obligatorio; code de un solo uso.
- `state` (CSRF) y `nonce` (replay) verificados.
- Rate limit en `/auth/authorize` y callbacks.
- Auditoría: `oauth.authorize`, `oauth.token`, `provider.link`, `login.failed`.
- Scopes por RP (least privilege).

---

## 7. Frontend

- Pantalla de login de osap-auth con botones "Continuar con Google / GitHub".
- Flujo de vinculación si el email ya existe.
- osap-api no tiene pantalla de login propia: solo redirige.

---

## 8. Decisiones abiertas

1. `email_verified`: confiar en el proveedor o exigir verificación propia.
2. Auto-registro al primer login social, o vínculo manual.
3. Unificar `service_clients` para los RP o crear `oauth_clients`.
4. ¿osap-api recibe `id_token`, solo access token, o ambos?

---

*Diseño v1 (2026-08). Detalle de implementación del lado osap-api: ver
`osap-api-oidc-integration-prompt-v1.md`.*
