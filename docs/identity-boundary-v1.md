# osap-auth — Identity Boundary v1 (preparación)

**Estado:** PREPARACIÓN. **No modifica el contrato congelado.**
**Ámbito:** este documento describe SOLO la frontera de identidad de osap-auth. No introduce
dependencia arquitectónica con osap-api u osap-storage. Las integraciones externas se
documentan en documentos de integración, no aquí.

---

# 1. Objetivo

Dejar preparado el contrato de identidad de osap-auth para soportar de forma explícita dos
tipos de principal autenticado — **USER** y **SERVICE** — sin modificar el contrato congelado
v1.0. Este documento describe el estado actual y los cambios candidatos (solo documentación;
no se implementan).

---

# 2. Frontera de identidad

osap-auth es responsable **exclusivamente** de:

- autenticación;
- identidad;
- emisión y validación de tokens;
- gestión de usuarios;
- sesiones;
- credenciales;
- scopes de servicio.

osap-auth responde **"¿quién eres?"**. No decide qué puede hacer un usuario dentro de ninguna
aplicación. No conoce reglas de negocio de obras, votos, compositores, proveedores,
estadísticas ni resolución.

---

# 3. Identidad de usuario

- `user_id`: **UUID opaco, estable, no reutilizable**. Es la única referencia de identidad de
  usuario que viaja entre aplicaciones.
- Nunca se usan email, nombre, `username`, `email_lookup` u otra PII como identificador.
- El access token (JWT) contiene los claims de identidad: `sub`, `jti`, `roles`,
  `email_verified` (sin PII).

## Claims del access token (v1.0, §10)

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

- Claims permitidos: los definidos en el contrato. Claims prohibidos: PII.
- Los claims describen **identidad**, no autorización.

---

# 4. Identidad de servicio

- Mecanismo: **OAuth2 `client_credentials`** → tokens de servicio JWT cortos.
- Endpoint: `POST /oauth/token` (`client_id` + `client_secret`).
- `service_id` = `client_id`. El secreto se guarda **hasheado**.
- Los tokens de servicio **no representan usuarios** y **no contienen identidad de usuario**.

## Scopes de servicio (v1.0, §12)

| Scope | Concede |
|---|---|
| `api:read` | lectura de datos de aplicación |
| `storage:read` | lectura de Works/resources |
| `auth:admin` | gestión de usuarios |
| `user.deleted:subscribe` | recibir evento de borrado |

---

# 5. Distinción USER / SERVICE (candidata, no implementada)

Para distinguir de forma inequívoca un user token de un service token se propone un claim
normativo:

```
token_use = "user" | "service"
```

**Estado:** el contrato v1.0 **no incluye** `token_use`. No se añade automáticamente.

### Dónde tendría que incorporarse (si se aprueba)
- Emisión de tokens en osap-auth (user tokens y service tokens).
- Documento: `osap-auth/docs/osap-auth-api-v1.0.md` §10 (user token) y §11 (service token).

### Impacto
- Claim **aditivo**: los validadores que ignoren claims extra no se rompen.
- Permite a los servicios validar el tipo de token sin heurísticas (presencia/ausencia de
  `roles` o `client_id`).

### Nota de independencia
La existencia de `token_use` es una decisión interna de osap-auth; **no** se documenta en este
contrato cómo la usan otras aplicaciones (eso queda en documentos de integración).

---

# 6. Autenticación vs autorización

- osap-auth solo **autentica**. No conoce ni aplica reglas de autorización de negocio.
- La decisión de qué operación puede ejecutar un principal pertenece a cada aplicación que
  ofrece la operación.

---

# 7. Cuestiones pendientes de osap-auth

1. Aprobar la emisión de `token_use` (user/service) — decisión contractual.
2. Confirmar que los scopes de servicio cubren las necesidades (los nuevos scopes de
   escritura/admin se documentan en documentos de integración, no aquí).
3. Rotación/revocación de secretos de service clients y expiración de service tokens.

---

# 8. Cambios futuros posibles (no implementados)

- Emitir `token_use` en user y service tokens.
- (Opcional) scopes adicionales de servicio cuando las aplicaciones los soliciten vía
  documentos de integración.
- Nada de esto modifica el contrato congelado v1.0 en esta fase.

---

*Documento de frontera de identidad de osap-auth v1 (2026-08) — preparación. Independiente de
osap-api/osap-storage.*
