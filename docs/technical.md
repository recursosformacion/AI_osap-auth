# OSAP Auth — Documentación técnica (v1.0)

**Estado:** implementado según el contrato `docs/osap-auth-api-v1.0.md`.
**Stack:** Python 3.11+, FastAPI, Pydantic v2, MySQL (aiomysql), Argon2id, JWT/JWKS,
AES-256-GCM, HMAC-SHA256.

---

# 1. Arquitectura por capas

```
api/            Capa HTTP (FastAPI). Schemas, dependencias, rutas, manejo de errores.
application/    Casos de uso (lógica de aplicación, sin IO).
domain/         Entidades, puertos (interfaces), servicios y excepciones.
infrastructure/ Persistencia (SQL), criptografía, JWT/JWKS, rate limiting, eventos, config.
```

Regla de dependencia: `api → application → domain` y `infrastructure → domain`.
`domain` no depende de nada. `application` depende solo de `domain`. La infraestructura
implementa los puertos del dominio e inyecta el contexto.

---

# 2. Puertos y sus implementaciones

| Puertos (domain/ports) | Implementación (infrastructure) |
|------------------------|---------------------------------|
| `UserRepository` | `SqlUserRepository` |
| `SessionRepository` | `SqlSessionRepository` |
| `TokenRepository` | `SqlTokenRepository` |
| `ServiceClientRepository` | `SqlServiceClientRepository` |
| `AuditRepository` | `SqlAuditRepository` |
| `RateLimiter` | `MemoryRateLimiter` (Redis en multi-instancia) |
| `PasswordHasher` | `Argon2PasswordHasher` (Argon2id) |
| `TokenHasher` | `HmacTokenHasher` (HMAC-SHA256 determinista) |
| `EmailProtector` | `AesGcmEmailProtector` (lookup HMAC + cipher AEAD) |
| `TokenProvider` | `PyJwtTokenProvider` (RS256 + JWKS) |
| `EventPublisher` | `LoggingEventPublisher` (registra `user.deleted`) |

---

# 3. Modelo de datos (BD `osap_auth`)

- `users`: `id` (UUID), `email_lookup`, `email_cipher`, `email_verified_at`,
  `password_hash`, `roles` (JSON), `status`, `key_version`, `created_at`, `updated_at`.
- `sessions`: `id` (jti), `user_id`, `refresh_token_hash`, `previous_refresh_token_hash`,
  `refresh_expires_at`, `created_at`, `last_used_at`, `revoked_at`, `ip`, `user_agent`,
  `device_label`.
- `tokens`: `id`, `user_id`, `purpose`, `token_hash`, `expires_at`, `used_at`, `created_at`.
- `service_clients`: `client_id`, `client_secret_hash`, `scopes` (JSON), `enabled`,
  `created_at`.
- `audit_events`: `id`, `event_type`, `actor`, `subject`, `ip`, `user_agent`, `outcome`,
  `context` (JSON), `prev_hash`, `hash`, `timestamp`.

El email **nunca** se guarda en claro: `email_lookup` (HMAC-SHA256 con pepper) solo para
localizar; `email_cipher` (AES-256-GCM) solo para mostrar.

---

# 4. Seguridad

- **Contraseñas**: Argon2id (irreversible, con sal).
- **Tokens opacos** (refresh, verificación, reset): digest **determinista** HMAC-SHA256
  con pepper. Racional: los tokens son aleatorios de alta entropía; un digest determinista
  permite localizarlos por valor para single-use/rotación/detección de reuso, sin guardarlos
  en claro y sin ser reversible. Argon2id queda reservado para contraseñas (secretos de
  baja entropía).
- **Access token** (JWT RS256, TTL 15 min): claims `iss`, `sub`, `aud`, `jti`, `roles`,
  `email_verified`, `iat`, `exp`, `scope`, `typ`. **Sin PII**. Verificación local vía JWKS
  (`GET /auth/.well-known/jwks.json`).
- **Refresh token**: opaco, rotado en cada refresh; el hash anterior queda en
  `previous_refresh_token_hash` para detectar reuso (revoca todas las sesiones del usuario).
- **Anti-enumeración**: respuestas genéricas + timing igualado (`dummy_verify`) + rate
  limiting por IP en login, registro, resend y reset.
- **Rate limiting**: sliding window en memoria.
- **Auditoría**: append-only con cadena de hashes (no-repudio). No guarda secretos ni PII.
- **Cifrado envolvente**: `key_version` por registro para rotar claves sin rediseñar la BD.
- **Auth ≠ Authorization**: osap-auth solo responde "quién eres"; las decisiones de
  autorización pertenecen a osap-api.

---

# 5. Endpoints

| Método | Path | Descripción |
|--------|------|-------------|
| `POST` | `/auth/register` | Crea cuenta `pending_verification` + token de verificación |
| `POST` | `/auth/verify-email` | Consume token de verificación (un solo uso) |
| `POST` | `/auth/resend-verification` | Reenvía verificación (rate-limited) |
| `POST` | `/auth/login` | Login → access + refresh + sesión |
| `POST` | `/auth/refresh` | Rota refresh (detección de reuso) |
| `POST` | `/auth/logout` | Revoca la sesión actual |
| `POST` | `/auth/logout-all` | Revoca todas las sesiones |
| `GET` | `/auth/sessions` | Lista sesiones |
| `DELETE` | `/auth/sessions/{id}` | Revoca una sesión |
| `POST` | `/auth/password-reset/request` | Solicita reset (respuesta genérica) |
| `POST` | `/auth/password-reset/confirm` | Confirma reset y revoca sesiones |
| `GET` | `/auth/me` | Perfil del usuario |
| `POST` | `/auth/me/password` | Cambio de contraseña (requiere actual) |
| `POST` | `/auth/me/email` | Inicia cambio de email |
| `POST` | `/auth/change-email/confirm` | Confirma cambio de email |
| `DELETE` | `/auth/me` | Borrado de cuenta (GDPR) + `user.deleted` |
| `POST` | `/oauth/token` | Service-to-service (`client_credentials`) |
| `GET` | `/auth/.well-known/jwks.json` | Claves públicas |
| `GET` | `/auth/version` | Versión del contrato |
| `GET` | `/health` | Health |

---

# 6. Notas de implementación

- El token de verificación se devuelve en la respuesta solo en entornos **no**
  productivos (`env != production`) para poder probar el flujo; en producción se envía por
  email.
- El evento `user.deleted` se registra y publica (colas/outbox reales quedan para una fase
  posterior); osap-api es quien anonimiza los votos.
- El rate limiter es de un solo proceso; en despliegue multi-instancia sustituir
  `MemoryRateLimiter` por una implementación distribuida con el mismo contrato.
- El cambio de email en v1.0 inicia la reverificación y registra el evento; el transporte
  seguro del nuevo email en el flujo de confirmación está señalado como pendiente.

---
*Documentación técnica de osap-auth v1.0 (2026-08).*
