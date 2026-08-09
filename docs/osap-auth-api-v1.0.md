# OSAP Auth API v1.0 — Contrato congelado

**Estado:** CONGELADO v1.0.
**Revisión:** basado en `osap-auth-proposal-v1.md` con los ajustes acordados
(email como campo secundario, osap-storage ajeno a usuarios, voto diseñado en el contrato,
separación Authentication/Authorization, **BD de identidad propia de osap-auth**).
**Regla de oro:** entre `osap-auth`, `osap-api` y `osap-storage` **solo viaja `user_id` (UUID)**.
El email y cualquier otro dato personal **nunca** son identificador entre aplicaciones.
Ver `_docs/architecture/OSAP_Persistence_Architecture_v1.md` para la propiedad y el cruce de
datos entre aplicaciones.

---

# 1. Principios

1. **osap-auth autentica; osap-api autoriza.** osap-auth responde "¿quién eres?".
   "¿Qué puede hacer aquí?" es siempre decisión del servicio que ofrece la operación.
2. **`user_id` es un UUID opaco, estable y sin significado.** Es la única referencia de
   identidad que viaja entre aplicaciones.
3. **osap-storage es ajeno a usuarios.** No conoce quién es el usuario, ni permisos, ni
   roles. Solo acepta tokens de servicio.
4. **Minimización de PII.** Los tokens de acceso no contienen email ni datos personales.
5. **Contraseñas irreversibles** (Argon2id). Nunca en claro ni cifrado reversible.
6. **osap-auth es propietario exclusivo de su base de datos de identidad.** Ningún otro
   servicio de OSAP accede directamente a esa BD; la comunicación entre servicios se hace
   exclusivamente por APIs/contratos, nunca por acceso directo a la BD de otro servicio.
7. **`user_id` se genera en osap-auth y es permanente** mientras exista la identidad.
   Se reutiliza en `osap-api` (p.ej. `votes.user_id`) y en futuros servicios de OSAP.

---

# 2. Modelo de usuario

## `users`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID (pk) | identidad estable y opaca; lo único que viaja entre apps |
| `email_lookup` | string (HMAC) | `HMAC-SHA256(email, pepper)` — **solo para localizar la cuenta** |
| `email_cipher` | bytes (AEAD) | email cifrado (AES-256-GCM, nonce por registro) — **solo para mostrar** |
| `email_verified_at` | timestamp? | null hasta verificación |
| `password_hash` | string | Argon2id |
| `roles` | lista de strings | `user`, `moderator`, `admin` |
| `status` | enum | `pending_verification`, `active`, `disabled`, `deleted` |
| `key_version` | int | rotación de claves de cifrado |
| `created_at`, `updated_at` | timestamps | |

## Persistencia y propiedad de datos

- osap-auth mantiene una **base de datos de identidad independiente** (p.ej. `osap_auth`).
- **Ningún otro servicio de OSAP accederá directamente a esta base de datos.**
- osap-auth es el **único responsable** de:
  - `users`
  - `sessions`
  - `refresh_tokens`
  - `verification` (tokens de verificación de email)
  - `password_reset` (tokens de recuperación)
  - `service_clients`
  - `audit` (auditoría de autenticación)
- osap-api mantiene **exclusivamente sus datos funcionales** (votos, estadísticas,
  resolución). osap-storage mantiene **exclusivamente sus datos de catálogo** (works,
  metadata, recursos).
- La comunicación entre servicios se realiza **exclusivamente mediante las APIs y contratos
  definidos, nunca mediante acceso directo a las bases de datos de otro servicio**.
- Cada aplicación es propietaria de sus datos y de su BD.

## `user_id` permanente

- El `user_id` (UUID) se **genera en osap-auth** en el registro.
- Es **permanente mientras exista la identidad**. No se reutiliza.
- Puede aparecer en osap-api (`votes.user_id`, estadísticas) y en futuros servicios OSAP,
  que guardan **solo el UUID opaco** y nunca datos de identidad (email, contraseña, sesiones).
- Al eliminar la cuenta, osap-auth emite `user.deleted` y osap-api anonimiza la referencia
  del voto conservando el agregado estadístico (ver §16).

### Roles de los dos campos de email

- `email_lookup` → **identificar/buscar** una cuenta (login, reset). Búsqueda de igualdad
  sin email en claro.
- `email_cipher` → **recuperar el email** cuando sea necesario (mostrar al usuario).

El email **no** es identificador entre aplicaciones: entre servicios solo viaja `user_id`.

---

# 3. Registro

`POST /auth/register`

- Entrada: `email`, `password` (+ política de contraseña).
- Crea usuario con `status = pending_verification`.
- Dispara token de verificación de email.
- Validaciones: email único, password cumple política.
- **Anti-enumeración**: si el email ya existe, responder de forma genérica (no revelar).

---

# 4. Verificación de email

- Token: **un solo uso**, **caduca** (24 h), **hasheado** en DB, alta entropía.
- `POST /auth/verify-email` marca `email_verified_at`, pasa a `active`.
- `POST /auth/resend-verification` (rate-limited).
- El **cambio de email** exige reverificación del nuevo email; tras confirmarse, el nuevo
  pasa a `email_lookup`/`email_cipher` y el viejo deja de resolver.

---

# 5. Login

`POST /auth/login`

- Autentica `email` (resuelto por `email_lookup`) + `password` (Argon2id).
- Respuesta genérica si el email no existe o la contraseña falla; **timing igualado**
  (hash Argon2id ficticio cuando la cuenta no existe) para no enumerar.
- Éxito → emite `access_token` + `refresh_token` y crea una **sesión**.
- Devuelve también `user_id`, `roles`, `email_verified` (para que el cliente sepa su estado).

---

# 6. Logout

- `POST /auth/logout` — revoca la **sesión actual**.
- `POST /auth/logout-all` — revoca **todas** las sesiones del usuario.
- `DELETE /auth/sessions/{id}` — revoca una sesión concreta (gestión de dispositivos).

---

# 7. Refresh

`POST /auth/refresh`

- Entrada: `refresh_token` opaco.
- **Rotación**: cada refresh invalida el anterior y emite uno nuevo.
- **Detección de reutilización**: si se reutiliza un refresh ya rotado → revocar **todas**
  las sesiones del usuario (señal de robo).
- Emite nuevo `access_token` + `refresh_token`.

---

# 8. Recuperación de contraseña

- `POST /auth/password-reset/request` — **siempre 200/202 genérico**, exista o no el email.
  Timing igualado con hash ficticio.
- Token: un solo uso, caduco (1 h), hasheado, alta entropía, límite de intentos.
- `POST /auth/password-reset/confirm` — cambia password, **revoca todas las sesiones**,
  marca el token usado.
- Cambio de contraseña autenticado: `POST /auth/me/password` (requiere password actual).

---

# 9. Sesiones

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID (pk) | = `jti` del access token |
| `user_id` | FK → users | |
| `refresh_token_hash` | string | Argon2id del refresh |
| `refresh_expires_at` | timestamp | |
| `created_at`, `last_used_at` | timestamps | |
| `revoked_at` | timestamp? | |
| `ip`, `user_agent`, `device_label` | string | contexto de sesión |

Soporta: listar dispositivos, revocar una, revocar todas, invalidar en cambio de
contraseña/reset.

---

# 10. JWT / JWKS

## Access token (JWT, stateless, TTL 15 min)

```json
{
  "iss": "https://auth.osap",
  "sub": "uuid-del-usuario",
  "aud": "osap-api",
  "jti": "uuid-de-la-sesion",
  "roles": ["user"],
  "email_verified": true,
  "scope": "openid profile api:vote",
  "token_use": "user",
  "iat": 1723000000,
  "exp": 1723000900
}
```

- **Sin PII**: sin email ni nombre. Solo `email_verified` (booleano).
- `aud` evita reutilizar un token emitido para un servicio en otro.
- `token_use = "user"` es el discriminador canónico de un access token de usuario
  (aditivo: los validadores que ignoren claims extra no se rompen). `typ = "access"`
  se mantiene por retrocompatibilidad.
- Firma: RS256/ES256. Claves públicas en `GET /auth/.well-known/jwks.json`.
- **Los claims describen identidad, no autorización.** No hay claim "puede votar": eso lo
  decide osap-api.
- TTL corto limita el alcance de un token robado. Revocación inmediata de un access token
  no es posible hasta su expiración (trade-off asumido y documentado).

## Refresh token (opaco, revocable, rotado)

- 128 bits aleatorios, **solo hasheado** (Argon2id).
- Rotación + detección de reutilización (ver §7).

---

# 11. Service-to-service authentication

- Mecanismo: **OAuth2 `client_credentials`** → tokens de servicio JWT cortos.
- Endpoint: `POST /oauth/token` (entrada: `client_id` + `client_secret`).
- Cada servicio tiene un `client_id`/`client_secret` (el secreto se guarda **hasheado**).
- **Scopes** por servicio (ver §12).
- El service token lleva `token_use = "service"` y `sub = client_id`; **no** contiene
  identidad de usuario (`roles`, `email_verified`, …). `typ = "service"` por
  retrocompatibilidad.
- Opcional en producción: **mTLS** como capa adicional de confianza en la red interna.

---

# 12. Scopes

| Scope | Concede | Uso |
|-------|---------|-----|
| `api:read` | leer datos de aplicación | osap-api → storage |
| `storage:read` | leer Works/resources de storage | osap-api → osap-storage |
| `storage:write` | escritura de datos en osap-storage (p. ej. votos) | osap-api → osap-storage |
| `storage:admin` | operaciones administrativas de osap-storage (compositores, fusiones) | cliente de administración → osap-storage |
| `auth:admin` | gestión de usuarios | osap-api (admin) → osap-auth |
| `user.deleted:subscribe` | recibir evento de borrado | osap-api → osap-auth |

Los scopes `storage:write` y `storage:admin` son de **grano grueso** (por servicio,
`client_credentials`). No amplían el significado de `storage:read`. La decisión de qué
operación concreta exige cada scope pertenece a **osap-storage**, no a osap-auth.

Regla firme: **los tokens de usuario y los de servicio son intransferibles.** osap-api nunca
reenvía el access token del usuario a osap-storage; storage solo acepta tokens de servicio con
el scope adecuado.

---

# 13. Cifrado y almacenamiento de datos personales

| Dato | Almacenamiento |
|------|----------------|
| Contraseña | Argon2id (hash con sal) |
| Refresh token / tokens de verificación/reset | hash (Argon2id) |
| Email (buscar) | `HMAC-SHA256(email, pepper)` → `email_lookup` |
| Email (mostrar) | AES-256-GCM (nonce por registro) → `email_cipher` |
| Otras PII sensibles | cifrado envolvente (DEK/KEK) |
| Roles / no sensibles | texto plano |

- **Cifrado envolvente**: DEK cifra los campos, guardado cifrado por la KEK (KMS/entorno
  protegido). `key_version` por registro para **rotación de claves**.
- Todo sobre TLS en tránsito.
- **Nota honesta** (trade-off aceptado): `email_lookup` es determinista; quien posea DB +
  pepper podría brute-forcear emails adivinables. Mitigar protegiendo el pepper y rotándolo.
  El email se asume como identificador semi-público.

---

# 14. Rate limiting

- Objetivos: `register`, `login`, `resend-verification`, `password-reset/request`,
  `password-reset/confirm`, y en producción todos los endpoints de usuario.
- Clave: **por IP** prioritariamente. El límite por cuenta existe pero con respuestas y
  tiempos **idénticos** (para no revelar existencia).
- Algoritmo: **sliding window**; contador distribuido (Redis) si hay varias instancias.
- **Evitar bloqueo permanente por cuenta** (permite DoS y enumera); preferir backoff temporal
  uniforme.

---

# 15. Auditoría

- Tabla **append-only** `audit_events`: `id`, `timestamp`, `event_type`, `actor`
  (user_id o client_id), `subject`, `ip`, `user_agent`, `outcome`, `context` (JSON), `hash`
  encadenado (no-repudio).
- Eventos mínimos: `register`, `email.verified`, `email.verify.failed`, `login`,
  `login.failed`, `logout`, `logout.all`, `session.revoked`, `refresh`,
  `password.reset.requested`, `password.reset.confirmed`, `password.changed`,
  `email.changed`, `role.changed`, `user.deleted`, `service.token.issued`.
- **No registrar** contraseñas, tokens ni emails completos.
- **Retención limitada** + purga programada (GDPR).

---

# 16. Borrado de cuenta y evento `user.deleted`

- `DELETE /auth/me` — cierre de cuenta por el usuario (GDPR, derecho al olvido).
- osap-auth marca `status = deleted`, purga/anonimiza sus datos según política, y **emite el
  evento `user.deleted`** para los suscriptores (osap-api).
- **Contrato del evento**: osap-api recibe `{ user_id, deleted_at }` y es responsable de
  **anonimizar los votos** (conservar el dato estadístico, eliminar la relación con el
  usuario). Ver `authentication-integration-v1.md`.

---

# 17. Integración con osap-api

- osap-api valida el access token **localmente** (JWKS) con `aud = osap-api`.
- Identidad por petición: `sub`, `jti`, `roles`, `email_verified`.
- **Autorización = decisión de osap-api** (p.ej. permitir votar exige `email_verified` + rol
  `user`, regla definida por osap-api).
- Detalle del perfil: `GET /auth/me` bajo demanda.
- Suscripción a `user.deleted` → anonimización de votos.
- Detalle en `osap-api/docs/authentication-integration-v1.md`.

---

# 18. Integración con osap-storage

- osap-storage **no conoce usuarios**. Solo autentica tokens de servicio con el scope
  `storage:read`.
- osap-auth no expone identidad de usuario a storage.
- Detalle en `osap-storage/docs/service-auth-v1.md`.

---

# 19. GDPR / retención

- **Minimización**: auth solo conoce identidad; api solo `user_id`; storage no conoce
  usuarios.
- Derecho de acceso/portabilidad: exportación del perfil.
- Derecho al olvido: `DELETE /auth/me` + evento `user.deleted`.
- Consentimiento registrado.
- Retención y purga de datos y logs tras plazos definidos.
- Seudonimización en tokens y logs (nunca email en claro en tránsito entre servicios).

---

# 20. Política de seguridad

- TLS en tránsito; cifrado en reposo; rotación de claves (DEK/KEK y JWKS).
- Argon2id con parámetros adecuados (memoria, tiempo, paralelismo).
- Anti-enumeración en login y reset (respuestas genéricas + timing + rate limit).
- No registrar PII en logs.
- Tokens nunca en URLs; guardado seguro en el cliente (httpOnly cookie o almacén seguro).
- CSRF si el cliente usa cookies para el refresh (SameSite + token CSRF).
- Sincronización de reloj y tolerancia de *clock skew* al validar `exp`/`iat`.
- Intransferencia de tokens entre servicios.

---

# 21. Versionamiento

- `GET /auth/version` → `{ "contract": "osap-auth-v1", "version": "1.0" }`.
- Semver de la API; cambios incompatibles → nueva versión mayor del contrato.

---
*Contrato congelado OSAP Auth API v1.0 (2026-08).*
