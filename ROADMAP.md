# ROADMAP — osap-auth (Identity Provider)

Rol en la arquitectura: **autoridad de identidad** (usuarios, credenciales, verificación de
email, sesiones, login, social login, OIDC, tokens).

Roadmap global de referencia: `_docs/roadmap.md` (raíz del proyecto).

---

## Fase B — OIDC (P1)

| Tarea | Estado |
|---|---|
| Discovery OIDC (`/.well-known/openid-configuration`) | ✅ |
| `/auth/authorize` y `/auth/authorize/complete` (code de un solo uso) | ✅ |
| Authorization Code + PKCE S256 + state + nonce | ✅ |
| `/oauth/token` (authorization_code, PKCE) | ✅ |
| `refresh_token` con rotación y detección de reuso | ✅ |
| Cliente OIDC `osap-api` registrado (dev y prod) | ✅ |
| Social login upstream (Google / GitHub) | 🟡 Pendiente |
| Mantener login email/password en la pantalla de login | ✅ |

## Fase G — Operación

| Tarea | Prioridad | Estado |
|---|---|---|
| Observabilidad (login, fallos, authorization codes, token exchange, social, refresh, eventos de seguridad) | P11 | 🟡 En evolución |
| Tests de contrato osap-auth ↔ osap-api (discovery, authorize, PKCE, callback, token, refresh, claims, `aud`, `token_use`) | P13 | 🟡 Pendiente |
| Despliegue separado (Servidor A/B/C; URL, TLS, secretos externos, config por entorno, health, logs, restart) | P14 | 🟡 En evolución |

---

## Estado actual

| Área | Estado |
|---|---|
| Registro + verificación de email | ✅ |
| Login email/password | ✅ |
| OIDC IdP (discovery, authorize, token, PKCE, refresh) | ✅ |
| Cliente `osap-api` registrado (dev y prod) | ✅ |
| Social login | 🟡 Pendiente |
| Observabilidad / eventos de seguridad | 🟡 En evolución |

---

## Criterio de cierre

- Un RP (osap-api) completa el flujo `Web → api → auth → api` con login email + social.
- El `client_secret` nunca se expone en respuestas ni en BD en claro.

*Fuente: `_docs/roadmap.md` (fases B y G).*
