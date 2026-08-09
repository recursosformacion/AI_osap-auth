# osap-auth — Prompt de implementación: `token_use` + scopes de servicio (v1)

**Estado:** PROMPT DE IMPLEMENTACIÓN (preparación). Al implementarlo, sigue el contrato
congelado `osap-auth-api-v1.0.md`. No introduce lógica de negocio de osap-api/osap-storage.

---

## Rol

Ingeniero sobre osap-auth. Implementa, en **osap-auth**, dos adiciones al modelo de tokens y
scopes, sin tocar la lógica de negocio de otras aplicaciones:

1. Emitir el claim **`token_use`** (`"user"` / `"service"`) en los tokens de acceso y de
   servicio.
2. Añadir los **scopes de servicio** `storage:write` y `storage:admin`.

El contrato interno de osap-auth debe permanecer **independiente** de osap-api/osap-storage.

---

## Principios

- osap-auth **autentica**; no decide qué operación puede ejecutar un principal.
- `user_id` (UUID opaco) es la única identidad de usuario que viaja entre apps.
- `service_id` = `client_id` para identidad de servicio.
- No se usa heurística para distinguir USER vs SERVICE: se usa `token_use`.
- Sin PII en tokens.

## Tier vs role (contexto transversal, no implementar claims aquí)

El modelo transversal distingue tres conceptos (ver `_docs/identity-and-authorization-v1.md`):

- `user_tier` — nivel de cuenta del usuario (free/basic/premium/...). **Concepto**; los nombres
  y la política quedan abiertos.
- `role` — capacidad funcional/administrativa (`user`, `moderator`, `admin`).
- `user_id` — UUID opaco.

**Este prompt NO añade `tier` ni `role` al JWT.** La distinción es un modelo conceptual para
osap-api; el único claim nuevo que se emite aquí es `token_use` (y los scopes de servicio).
`tier` y `role` son atributos del usuario gestionados por osap-auth, pero no viajan en el token
en esta fase (no introducir claims en silencio).

---

## 1. `token_use`

Añadir el claim `token_use` a los JWT emitidos por osap-auth:

```json
{ "token_use": "user" }     // en el access token de usuario
{ "token_use": "service" }  // en el service token (client_credentials)
```

### Reglas
- **Access token de usuario** (login/refresh): `token_use = "user"`.
- **Service token** (OAuth2 `client_credentials`): `token_use = "service"`.
- `token_use` es un claim **aditivo**: los validadores que ignoren claims extra no se rompen.
- **Nunca** se infiere `token_use` por presencia/ausencia de `roles` o `client_id`.

### Dónde tocar
- Emisión del JWT de usuario (`sub`, `jti`, `roles`, `email_verified`, `scope`, …).
- Emisión del JWT de servicio (`client_credentials` → `POST /oauth/token`).
- Documento del contrato: actualizar `osap-auth/docs/osap-auth-api-v1.0.md` §10 (user token) y
  §11 (service token) para listar `token_use` entre los claims.

### Tests
- Un user token emitido tiene `token_use == "user"`.
- Un service token emitido tiene `token_use == "service"`.
- Un service token **no** contiene identidad de usuario (`sub` = client_id; sin `roles` de
  usuario).
- La validación del JWKS sigue aceptando tokens sin `token_use` (retrocompatibilidad) o lo
  trata según la política acordada (decisión: ¿exigir `token_use` o tolerar su ausencia?).

---

## 2. Scopes de servicio

Añadir a la tabla/contrato de scopes:

| Scope | Concede |
|---|---|
| `storage:write` | escritura de datos en osap-storage (p. ej. votos) |
| `storage:admin` | operaciones administrativas de osap-storage (compositores, fusiones) |

### Reglas
- Scopes de **grano grueso**, por servicio (client_credentials).
- No se amplía el significado de `storage:read`.
- La **decisión** de qué operación requiere qué scope pertenece a osap-storage (no a osap-auth).
- Se asignan a los `service_clients` correspondientes (osap-api, y el que gestione la
  administración de compositores).

### Dónde tocar
- Emisión/validación de service tokens (`POST /oauth/token`) para admitir los nuevos scopes.
- Registro/asignación de scopes a `service_clients`.
- Documento del contrato: actualizar `osap-auth/docs/osap-auth-api-v1.0.md` §12 (tabla de
  scopes).

### Tests
- Un service token de osap-api puede solicitar y recibir `storage:write` y `storage:admin`.
- Un `client_id` sin ese scope no puede obtenerlo.
- Los scopes se reflejan en el claim `scope` del service token.

---

## 3. Independencia del contrato

- osap-auth no añade reglas de negocio de obras/votos/compositores/proveedores/estadísticas.
- No referencia a osap-api/osap-storage en el contrato interno; solo los scopes y `token_use`.
- Las integraciones externas se documentan en documentos de integración.

---

## 4. Retrocompatibilidad

- `token_use` y los nuevos scopes son **aditivos**.
- Decisión a aprobar: si un token sin `token_use` debe rechazarse o tratarse como
  "user legado". Propuesta: tolerar su ausencia durante la transición y exigirlo tras la
  congelación de la siguiente versión.

---

## 5. NO implementar

- No añadir claims de `tier` ni `role` al JWT (son un modelo conceptual para osap-api, no un
  claim de token en esta fase).
- No asumir que `admin` sea un tier; `admin` es un rol (decisión transversal abierta).
- No modificar la lógica de votos, estadísticas ni compositores.
- No cambiar el modelo de usuario, contraseñas, sesiones ni email.
- No tocar osap-api ni osap-storage.
- No desplegar ni migrar producción sin aprobación.

---

## 6. Validación

Al terminar, en osap-auth:
- ejecutar los tests existentes;
- `ruff`, `mypy`, `pytest` limpios;
- confirmar que no se ha alterado el comportamiento previo.

---

*Prompt de implementación de osap-auth v1 (2026-08) — `token_use` + scopes `storage:write`/`storage:admin`.*
