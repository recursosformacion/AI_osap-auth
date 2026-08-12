# PROMPT PARA OSAP-API — Integrar login vía osap-auth como IdP OIDC

Entregar este documento al agente de **osap-api**. Es autocontenido; el contrato del lado
osap-auth está en `osap-auth/docs/social-login-and-oidc-v1.md`.

---

## Rol

Trabajas sobre **osap-api** (NO tocas osap-auth). Debes migrar el login del Web de osap-api
para que **deje de usar su formulario de email/password** y, en su lugar, **redirija el
navegador a la pantalla de login hosteada por osap-auth** (OIDC Authorization Code + PKCE).
No añades reglas de negocio nuevas ni tocas la lógica de votos/works/compositores.

## Contexto actual en osap-api

- Frontend (Web):
  - `web/src/api/AuthClient.ts` — hoy llama a `/auth/login` y `/auth/refresh` contra osap-auth.
  - `web/src/state/auth.ts` — store Zustand; access token en memoria, refresh en `localStorage`.
- Backend:
  - `src/osap/infrastructure/auth/token_authenticator.py` — `JwtAuthenticator` ya resuelve
    `Principal` por `token_use` (`user`/`service`) validando firma/JWKS localmente.
  - `src/osap/infrastructure/auth/auth_proxy_client.py` — cliente HTTP hacia osap-auth.
  - `src/osap/bootstrap/wiring.py` — construcción de dependencias y `JwtAuthenticator`.

## Contrato con osap-auth (lo que osap-auth ofrecerá)

osap-auth expondrá un flujo OIDC estándar. osap-api actúa como *relying party* con
`client_id=osap-api`:

1. **Redirigir el navegador** a:

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

2. **Callback** en la `redirect_uri`: recibir `?code=...&state=...` (validar `state`).
3. **Canjear el code** en `POST /oauth/token`:
   - `grant_type=authorization_code`
   - `client_id=osap-api`
   - `client_secret=<...>`
   - `redirect_uri=...`
   - `code=...`
   - `code_verifier=...` (PKCE)
   - Respuesta: `access_token`, `refresh_token`, `token_type`, `expires_in`, `scope`.

Nota de endpoints: en producción el API de osap-auth se sirve bajo el prefijo `/auth-api`
(`https://auth.openmusicrepository.com/auth-api/...`); osap-auth confirmará el valor exacto
de `token_url`/`authorize_url` que debe usar.

## Qué hacer en osap-api

1. **Backend**
   - Añadir un cliente del flujo OIDC RP (PKCE): generar `verifier`/`challenge`, construir la
     URL de `authorize`, validar `state`/`nonce`, canjear el code en `/oauth/token`.
   - Endpoint(s) de callback: recibir el code y devolver la sesión al Web (emitir/guardar el
     access + refresh de forma segura).
   - Mantener/usar `JwtAuthenticator` para validar los **access tokens de usuario**
     (`sub=user_id`, `token_use=user`, `aud=osap-api`) en las APIs de usuario.
   - Config (extender `Configuration`/`wiring`): `authorize_url`, `token_url`, `client_id`,
     `client_secret`, `redirect_uri`. Secretos por variable de entorno (nunca commitear).
2. **Frontend**
   - Reemplazar el formulario de login por "Continuar con cuenta OSAP": redirigir a la URL de
     `authorize`; en el callback, almacenar refresh (localStorage, con rotación) y access en
     memoria, igual que hoy (`web/src/state/auth.ts`).
   - Conservar el comportamiento de refresh/logout.
3. **Privilegios mínimos**: solicitar únicamente los scopes necesarios. No pedir roles/tier.
4. **Documentación**: actualizar `docs/authentication-integration-v1.md` con el nuevo flujo.

## Distinción de tokens (importante)

- Token de **usuario** (`sub=user_id`, `token_use=user`) → para APIs de usuario.
- Token de **servicio** (`sub=client_id`, `token_use=service`) → ya lo usas para
  machine-to-machine hacia osap-storage (no cambiar).
- No mezclar: el refresh/login del usuario no debe usar el flujo `client_credentials`.

## Seguridad

- PKCE obligatorio; code de un solo uso.
- Validar `state` (CSRF) y `nonce` (replay).
- El `client_secret` solo en el backend, por variable de entorno.

## Fuera de alcance

- No tocar osap-auth.
- No cambiar la lógica de votos, works, compositores ni estadísticas.
- No desplegar producción sin aprobación.

## Validación

- Tests existentes en osap-api siguen verdes (especialmente `tests/osap/test_identity_authorization.py`
  y los tests de Web `auth`).
- Flujo manual: redirigir a osap-auth, autenticarse (email o social), recibir code, canjearlo
  y obtener un access token de usuario con `token_use=user`.

---

*Prompt de integración para osap-api v1 (2026-08).*
