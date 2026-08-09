# OSAP-Auth — Propuesta arquitectónica independiente (v1.0)

**Estado:** propuesta para revisión. No es el contrato congelado.
**Propósito:** plantear una arquitectura de identidad/autenticación para OSAP de forma
independiente, para compararla después con la propuesta del equipo antes de congelar v1.0.

---

# 1. Evaluación crítica de la separación de responsabilidades

La separación `osap-auth` / `osap-api` / `osap-storage` es conceptualmente correcta y
coincide con la filosofía del Architecture Book. Hay **tres puntos que conviene cerrar ya**
porque condicionan todo lo demás:

## 1.1 La dependencia identidad → datos de aplicación (votos)

El caso de uso "voto de obra" cruza los dos dominios:

- **osap-auth** conoce al usuario (identidad).
- **osap-api** guarda los votos (lógica de aplicación).

Esto obliga a congelar un contrato de **identidad estable** (`user_id` opaco tipo UUID) y,
sobre todo, una **política de borrado (GDPR)**: cuando un usuario ejerce el derecho al
olvido y se borra en osap-auth, ¿qué pasa con sus votos en osap-api?

- Opción A — **Anonimizar**: se borra la relación `user_id` pero se conservan los votos
  (necesarios para las valoraciones de obras/compositores) y se recalcula. Sin eliminar
  el dato agregado.
- Opción B — **Eliminar**: se borran los votos del usuario y se recalcula el agregado.

Recomendación: **A (anonimizar)** para conservar la integridad de las estadísticas, con
`user_id` sustituido por un pseudónimo o marcado como "cuenta eliminada". **Debe congelarse
en v1.0**, y requiere un mecanismo de propagación auth → api (evento/webhook), no una
consulta puntual.

## 1.2 osap-storage debe rechazar tokens de usuario

osap-storage solo debe ser accesible internamente y **nunca con la identidad del usuario**.
Debe aceptar únicamente **tokens de servicio** (máquina a máquina) con un *scope* concreto.
De este modo, un token de usuario filtrado nunca da acceso a storage.

Regla de diseño: **los tokens de usuario y los tokens de servicio son intransferibles**.
osap-api nunca debe reenviar el access token del usuario hacia osap-storage.

## 1.3 Disponibilidad: la lectura pública no debe depender de osap-auth

La búsqueda/consulta pública de obras pasa por osap-api/osap-storage y **no debe requerir**
que osap-auth esté disponible. La autenticación solo debe ser necesaria en los endpoints
que la exigen (votar, perfil, admin). No centralices el tráfico de lectura a través de auth.

## Conclusión de la sección

La separación es correcta; el único riesgo real es el **acoplamiento identidad ↔ votos** y el
**ciclo de vida de la cuenta** (borrado, cambio de email, roles cambiantes). Todo lo demás se
resuelve con contratos de tokens y claims bien definidos.

---

# 2. Decisiones arquitectónicas fundamentales

## 2.1 Modelo de token/sesión (recomendación)

Modelo híbrido, estándar y que satisface "sesiones revocables":

- **Access token**: JWT firmado (RS256/ES256), **corto** (TTL 15 min), **stateless**.
  osap-api lo valida localmente contra un **JWKS** público (sin llamada a auth por petición).
- **Refresh token**: **opaco** (128 bits aleatorios), guardado **solo como hash** (Argon2id)
  en la tabla de sesiones, **revocable**, con **rotación** y **detección de reutilización**.
  TTL p.ej. 30 días (sliding) con tope absoluto.
- **Sesión**: fila en DB que da soporte a listar/revocar una, revocar todas, invalidar en
  cambio de contraseña/reset.

### Trade-off que debe quedar explícito en v1.0

Un access token JWT stateless **no puede revocarse al instante**: si se revoca una sesión, el
access token sigue válido hasta su expiración (máx. 15 min). Esto es aceptable y estándar.
Revocación inmediata implicaría *introspection* por petición (más latencia). En v1.0 se
congela: **TTL corto + revocación vía refresh/sesión**.

## 2.2 Identidad hacia osap-api

osap-api valida el access token **localmente** (JWKS). No llama a osap-auth en runtime para
la identidad. Para casos de detalle (perfil) existe `GET /auth/me` protegido. La verificación
de firma se apoya en JWKS cacheado y gestión de rotación de claves.

## 2.3 Autenticación entre servicios

Recomendación: **OAuth2 `client_credentials`** (tokens de servicio JWT cortos, con *scope*),
con la posibilidad de añadir **mTLS** en producción como capa adicional.

| Servicio | Autentica contra auth | Emite | Lo que acepta |
|----------|----------------------|-------|----------------|
| osap-api | ✓ (service token) | usa tokens de usuario y de servicio | user token (JWT) + service token (JWT, scope `api:...`) |
| osap-storage | ✓ (service token) | — | **solo** service token (scope `storage:...`), nunca user token |

---

# 3. Modelo de datos

## 3.1 `users`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID (pk) | identidad estable, opaco, para osap-api |
| `email_lookup` | string (HMAC) | HMAC-SHA256(email, pepper) con índice único → búsqueda sin email en claro |
| `email_cipher` | bytes (AEAD) | email cifrado (AES-256-GCM, nonce por registro) → solo para mostrar |
| `email_verified_at` | timestamp? | null hasta verificación |
| `password_hash` | string | Argon2id (hash, nunca reversible) |
| `roles` | lista de strings | `user`, `admin`, `moderator` |
| `status` | enum | `pending_verification`, `active`, `disabled`, `deleted` |
| `key_version` | int | para rotación de claves de cifrado |
| `created_at`, `updated_at` | timestamps | |

## 3.2 `sessions`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID (pk) | = `jti` del access token |
| `user_id` | FK → users | |
| `refresh_token_hash` | string | Argon2id del refresh token |
| `refresh_expires_at` | timestamp | |
| `created_at`, `last_used_at` | timestamps | |
| `revoked_at` | timestamp? | revocación explícita |
| `ip`, `user_agent`, `device_label` | string | contexto de la sesión (para listar "mis dispositivos") |

## 3.3 `email_verifications` / `password_resets`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID | |
| `user_id` | FK | |
| `token_hash` | string | hash del token de un solo uso (nunca en claro) |
| `purpose` | enum | `verify_email`, `reset_password` |
| `expires_at` | timestamp | caducidad |
| `used_at` | timestamp? | un solo uso |
| `created_at` | timestamp | |

## 3.4 `audit_events`

Tabla **append-only** de eventos de seguridad (ver §11).

## 3.5 `service_clients` (para machine-to-machine)

| Campo | Tipo | Notas |
|-------|------|-------|
| `client_id` | string | |
| `client_secret_hash` | string | Argon2id del secreto |
| `scopes` | lista | p.ej. `storage:read` |
| `enabled` | bool | |

---

# 4. Endpoints de osap-auth

| Método | Path | Acceso | Descripción |
|--------|------|--------|-------------|
| `POST` | `/auth/register` | público | crea cuenta (status `pending_verification`) y dispara verificación |
| `POST` | `/auth/verify-email` | público | consume token de verificación (un solo uso, caduca) |
| `POST` | `/auth/resend-verification` | público | reenvía email de verificación (rate-limited) |
| `POST` | `/auth/login` | público | autentica email+password → access + refresh |
| `POST` | `/auth/logout` | usuario | revoca la sesión actual |
| `POST` | `/auth/logout-all` | usuario | revoca todas las sesiones |
| `GET` | `/auth/sessions` | usuario | lista sesiones activas (dispositivos) |
| `DELETE` | `/auth/sessions/{id}` | usuario | revoca una sesión |
| `POST` | `/auth/refresh` | refresh token | emite nuevo access (+ rota refresh) |
| `POST` | `/auth/password-reset/request` | público | envía email de reset (respuesta genérica) |
| `POST` | `/auth/password-reset/confirm` | público | consume token, cambia password, revoca sesiones |
| `GET` | `/auth/me` | usuario | perfil (id, email, roles, email_verified) |
| `PATCH` | `/auth/me` | usuario | cambio de email (requiere reverificación) / perfil |
| `POST` | `/auth/me/password` | usuario | cambio de contraseña con password actual |
| `DELETE` | `/auth/me` | usuario | cierre de cuenta (GDPR) → evento de anonimización a api |
| `POST` | `/auth/change-email/confirm` | público | confirma nuevo email con token |
| `GET` | `/auth/.well-known/jwks.json` | público | claves públicas para validar access tokens |
| `POST` | `/oauth/token` | service | `client_credentials` → token de servicio |
| `GET` | `/auth/version` | público | versión del contrato |

**Admin (role `admin`):** endpoints de gestión de usuarios (listar, buscar, activar/desactivar,
cambiar roles, reenviar verificación, forzar revocación de sesiones).

---

# 5. Modelo de sesión/token (detalle)

## Access token (JWT, stateless)

```json
{
  "iss": "https://auth.osap",
  "sub": "uuid-del-usuario",
  "aud": "osap-api",
  "jti": "uuid-de-la-sesion",
  "roles": ["user"],
  "email_verified": true,
  "iat": 1723000000,
  "exp": 1723000900,
  "scope": "openid profile api:vote"
}
```

Principios:
- **No incluir PII** (ni email ni nombre) en el token; solo el `email_verified` como booleano.
  Si osap-api necesita mostrar el email, lo pide a `/auth/me`, no lo lee del token.
- `aud` evita que un token emitido para un servicio se use en otro.
- TTL corto limita el alcance de un token robado.

## Refresh token (opaco, revocable, rotado)

- 128 bits aleatorios, almacenado **solo hasheado** (Argon2id).
- **Rotación**: cada refresh invalida el anterior y emite uno nuevo.
- **Detección de reutilización**: si se reutiliza un refresh ya rotado → revocar **todas** las
  sesiones del usuario (señal de robo).

## Flujo de acceso

```
login → access(15') + refresh(30d) [sesión creada]
  cada petición → osap-api valida access localmente (JWKS)
  al vencer access → POST /auth/refresh → nuevo access + refresh rotado
  logout → revoca sesión (invalida refresh)
```

---

# 6. Comunicación osap-auth → osap-api

- **Identidad por petición**: JWT validado localmente (JWKS). Claims: `sub`, `jti`, `roles`,
  `email_verified`, `aud`, `exp`.
- **Regla de votación**: osap-api exige `email_verified == true` + rol `user` para votar.
- **Detalle del usuario**: `GET /auth/me` (opcional, bajo demanda).
- **Propagación de borrado**: osap-auth emite evento/webhook `user.deleted` → osap-api
  anonimiza/borra los votos del `sub`. Contrato a congelar en v1.0.

---

# 7. Autenticación entre servicios

- **osap-api ↔ osap-auth**: `client_credentials` → service token (scope `auth:*`).
- **osap-api ↔ osap-storage**: osap-api obtiene service token (scope `storage:read`) y lo usa
  para llamar a storage. **osap-storage rechaza** tokens de usuario (solo valida firma de
  service token + scope). Los tokens de servicio son **cortos** y se obtienen bajo demanda.
- **mTLS** (opcional, producción) como capa de confianza adicional en la red interna.

Regla firme: **nunca reenviar el access token del usuario a otro servicio**.

---

# 8. Almacenamiento y protección de datos personales

| Dato | Almacenamiento |
|------|----------------|
| Contraseña | **Argon2id** (hash con sal, nunca reversible) |
| Refresh token / tokens de verificación/reset | **hash** (Argon2id) |
| Email (para buscar) | **HMAC-SHA256(email, pepper)** → columna `email_lookup` indexada |
| Email (para mostrar) | **cifrado AEAD** (AES-256-GCM, nonce por registro) → `email_cipher` |
| Otras PII sensibles | cifrado de campo con cifrado envolvente (DEK/KEK) |
| Roles / datos no sensibles | texto plano |

### Nota sobre búsqueda por email sin claro

La columna `email_lookup` (HMAC) permite búsquedas de igualdad **sin guardar el email en
claro**. Limitación honesta: el HMAC es determinista, así que quien posea la DB + el pepper
podría brute-forcear emails adivinables. Mitigaciones: proteger el pepper, rotarlo
(`key_version`), y asumir que el email es un identificador semi-público. Es la práctica
estándar (p.ej. listas de suscripción). Documentar el trade-off; no ocultarlo.

### Cifrado envolvente

- **DEK** (data encryption key) cifra los campos; se guarda cifrado por la **KEK** (key
  encryption key) fuera del servicio (KMS / variable de entorno protegida).
- `key_version` por registro para **rotación de claves** sin reescribir todo de golpe.
- Todo el cifrado sobre TLS en tránsito.

---

# 9. Verificación de email

1. `POST /auth/register` crea usuario `pending_verification` y emite token de verificación.
2. Token: **un solo uso**, **caduca** (p.ej. 24 h), **hasheado** en DB, alta entropía.
3. `POST /auth/verify-email` valida, marca `email_verified_at`, pasa a `active`.
4. `POST /auth/resend-verification` (rate-limited) reenvía.
5. El **cambio de email** (PATCH /auth/me) exige **reverificación** del nuevo email; el viejo
   deja de servir para `email_lookup` tras confirmarse.

---

# 10. Recuperación de contraseña

Flujo anti-enumeración:

1. `POST /auth/password-reset/request` — **siempre 200/202 genérico**, tanto si el email
   existe como si no.
2. Igualar tiempos: si el email no existe, ejecutar igualmente un hash Argon2id ficticio
   para no revelar existencia por timing.
3. Token: un solo uso, caduco (p.ej. 1 h), hasheado, alta entropía, con **límite de intentos**.
4. `POST /auth/password-reset/confirm` cambia la contraseña, **revoca todas las sesiones** y
   marca el token usado.
5. Nunca revelar en la respuesta si el email existía.

---

# 11. Roles y permisos

- Roles en v1.0: `user`, `moderator`, `admin`.
- Se transportan como **claims** en el access token; osap-api/osap-auth los aplican.
- Los roles viven en osap-auth; los cambios de rol **revocan sesiones** (o se asumen con
  efecto al expirar el access token, TTL corto lo limita).
- Mantener **RBAC simple** (rol → lista de permisos) sin inventar un sistema de permisos
  fino en v1.0.
- `admin` gestiona usuarios; `moderator` (futuro) para curaduría de obras/compositores.

---

# 12. Auditoría

- Tabla **append-only** `audit_events`: `id`, `timestamp`, `event_type`, `actor` (user_id o
  client_id), `subject`, `ip`, `user_agent`, `outcome`, `context` (JSON), `hash` (encadenado
  para no-repudio).
- Eventos mínimos v1.0: `register`, `email.verified`, `email.verify.failed`, `login`,
  `login.failed`, `logout`, `logout.all`, `session.revoked`, `refresh`,
  `password.reset.requested`, `password.reset.confirmed`, `password.changed`,
  `email.changed`, `role.changed`, `user.deleted`, `service.token.issued`.
- **No registrar** contraseñas, tokens, ni emails completos en logs.
- Política de **retención** (GDPR): retención limitada + purga programada.

---

# 13. Rate limiting

- Objetivos: `register`, `login`, `resend-verification`, `password-reset/request`,
  `password-reset/confirm`, y en producción todos los endpoints de usuario.
- Clave: **por IP** prioritariamente; el límite **por cuenta** puede revelar existencia si no
  se devuelve la misma respuesta. Usar ambos pero con respuestas idénticas y tiempos igualados.
- Algoritmo: **sliding window**. Si hay varias instancias, usar un contador distribuido
  (p.ej. Redis).
- **Evitar bloqueo permanente por cuenta** (permite DoS y enumera); preferir backoff temporal
  uniforme.

---

# 14. Privacidad / GDPR

- **Minimización**: auth solo conoce identidad; api solo `sub`; storage no conoce usuarios.
- **Derecho de acceso/portabilidad**: endpoint de exportación del perfil.
- **Derecho al olvido**: `DELETE /auth/me` + evento de anonimización a osap-api (votos).
- **Consentimiento**: registrar cuándo y qué datos se aceptan.
- **Retención**: borrado/purga de datos y logs tras plazos.
- **Seudonimización** en lugar de PII en tokens y logs.
- **DPIA** y registro de actividades de tratamiento si se trata a gran escala.

---

# 15. Problemas de seguridad clave a mitigar

1. **Enumeración de usuarios** — mitigar con respuestas genéricas + timing igualado + rate
   limiting por IP (login y reset).
2. **Credential stuffing** — Argon2id (coste alto) + rate limiting + opción de lista de
   contraseñas comprometidas (puede ser v2).
3. **Bloqueo por cuenta como vector DoS** — preferir rate limit a lockout permanente.
4. **Robo de token** — TTL corto, rotación de refresh, detección de reutilización, TLS,
   no exponer tokens en URLs, guardado seguro (httpOnly cookie o almacenamiento seguro del
   cliente).
5. **CSRF** — si el cliente usa cookies para el refresh, proteger con SameSite/CSRF token.
6. **Brute-force del token de reset/verificación** — alta entropía + caducidad + límite de
   intentos.
7. **Fuga de email** — HMAC + cifrado AEAD + pepper separado de la DB.
8. **Claves de firma** — rotación de JWKS coordinada entre auth y api; no mezclar firmar y
   cifrar con la misma clave.
9. **Inyección por email** (cabeceras) — sanear/escapar el email en el envío de emails.
10. **Logging de PII** — nunca emails/tokens/contraseñas en logs.
11. **Sincronización de reloj** — tolerancia de *clock skew* al validar `exp`/`iat`.
12. **Intransferencia de tokens** — storage solo acepta tokens de servicio.

---

# 16. Qué congelar en v1.0

- [ ] Modelo de token/sesión: access JWT (15') + refresh opaco rotado + sesión en DB.
- [ ] `user_id` opaco (UUID) como única referencia de identidad hacia osap-api.
- [ ] Claims del token (sub, jti, roles, email_verified, aud, scope). Sin PII en el token.
- [ ] Firma JWT vía JWKS + validación local por osap-api (aud/iss/exp).
- [ ] Autenticación entre servicios: OAuth2 `client_credentials` + scopes. Storage solo
    acepta tokens de servicio.
- [ ] Regla de votación: `email_verified` + rol `user`; "1 voto por usuario por obra/día"
    con día en **UTC**.
- [ ] Política de borrado de cuenta → anonimización de votos en osap-api (evento auth→api).
- [ ] Almacenamiento: Argon2id para secretos; HMAC+pepper para email_lookup; cifrado AEAD
    para email mostrable; cifrado envolvente + `key_version`.
- [ ] Flujos anti-enumeración en login y reset (respuestas genéricas + timing + rate limit).
- [ ] Tabla `audit_events` append-only + retención.
- [ ] Versión del contrato expuesta (`/auth/version`) y semver de la API.

---

# 17. Qué dejar para versiones posteriores

- Federación: **OAuth2/OIDC social** (Google, GitHub...), SAML/SSO corporativo.
- **MFA / TOTP / passkeys**.
- Gestión de dispositivos avanzada (revocación remota con notificación).
- Lista de contraseñas comprometidas (credential stuffing a escala).
- Permisos finos (ABAC) si la RBAC simple se queda corta.
- Recovery por teléfono / segunda vía.
- Notificaciones push / alertas de inicio de sesión.
- Análisis de riesgo / detección de anomalías basada en el log de auditoría.
- Multi-tenant / organizaciones.

---

# 18. Dependencias arquitectónicas de riesgo

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Borrado de cuenta ↔ votos | Pérdida de estadísticas o dato personal persistido | Contrato de anonimización auth→api en v1.0 |
| Cambio de email ↔ identidad en api | Referencias desactualizadas | api usa solo `sub`, nunca email |
| Roles cambiantes ↔ tokens en circulación | Permisos obsoletos hasta TTL | TTL corto + revocar sesiones en cambio de rol |
| Claves de firma ↔ múltiples validadores | Tokens inválidos tras rotación | Gestión de rotación JWKS coordinada |
| Disponibilidad de auth ↔ lectura pública | Caída de auth bloquea todo | auth solo en endpoints protegidos; lectura sin auth |
| Semántica de "día" del voto | Doble voto por zona horaria | fijar día en UTC |

---

# 19. Resumen

La arquitectura propuesta es sólida y la separación de responsabilidades correcta. Los dos
puntos que exigen decisión explícita antes de congelar v1.0 son:

1. **Token/sesión**: access JWT corto + refresh opaco rotado + sesión revocable en DB.
2. **Ciclo de vida de la cuenta**: política de anonimización de votos en osap-api al borrar
   la cuenta, y propagación del evento auth → api.

El resto son decisiones de detalle (claims, scopes, algoritmos, rate limiting, auditoría) que
este documento concreta y que deben quedar recogidas en el contrato **OSAP Auth API v1.0**
antes de escribir cualquier código.

---
*Documento de propuesta (2026-08). No es el contrato congelado.*
