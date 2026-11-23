# OSAP Auth — Identity and Authentication Service

**OSAP Auth** is the identity and authentication service for the [OSAP — Open Score Acquisition Platform](https://github.com/recursosformacion/AI_GAMEPC2) ecosystem. It is maintained as a separate Python service.

The project provides the authentication foundation used by other OSAP services. The ecosystem uses signed service JWTs and JWKS-based public-key verification; consult the implementation and deployment configuration in this repository for the exact contracts and settings.

## Technology

- Python 3.11+
- FastAPI and Uvicorn
- Pydantic settings
- MySQL/MariaDB and Alembic
- Argon2, cryptography and PyJWT
- pytest, Ruff and mypy for development checks

## Related OSAP repositories

- **[AI_GAMEPC2](https://github.com/recursosformacion/AI_GAMEPC2)** — OSAP core and resource-resolution engine.
- [ai-importacion](https://github.com/recursosformacion/ai-importacion) — independent discovery and review of music materials from Internet Archive.
- [ai_recogeYouTube](https://github.com/recursosformacion/ai_recogeYouTube) — discovery and review of YouTube recordings associated with musical works.
- [AI_osap-storage](https://github.com/recursosformacion/AI_osap-storage) — authoritative catalogue-data and storage service.
- [AI_osap-support](https://github.com/recursosformacion/AI_osap-support) — donations, memberships and support services.
- Public catalogue: [openmusicrepository.com](https://openmusicrepository.com)

## Development

Install the project and development dependencies according to the repository's packaging configuration. Use the repository's test and lint configuration before proposing changes. Deployment secrets and environment-specific credentials must be supplied through configuration, not committed to source control.


## Production configuration

Use [`config.production.example.yaml`](config.production.example.yaml) as the production
template and copy it to `config.yaml` on the server. The issuer is the root Auth origin
(`https://auth.openmusicrepository.com`); the public base URL includes the reverse-proxy
prefix (`/auth-api`). Supply every `${OSAP_AUTH_*}` placeholder through the service
environment or secret manager. Production startup rejects unresolved placeholders, missing
cryptographic keys, missing SMTP host, and non-HTTPS public issuer/URL settings.

## Cliente M2M dedicado para administración de Support

`osap-api` utiliza un cliente de servicio independiente para operaciones administrativas
contra `osap-support`. El provisionador `scripts/provision_support_admin_client.py`
reconcilia de forma idempotente el estado declarado:

- UUID: `OSAP_SUPPORT_ADMIN_CLIENT_ID`
- Secreto: `OSAP_SUPPORT_ADMIN_CLIENT_SECRET`
- Audiencia única: `osap-support`
- Scope único: `support:admin`

Auth almacena únicamente el hash HMAC del secreto. El UUID y el secreto deben ser los
mismos que se configuren en el entorno de desarrollo de `osap-api`; no se generan
identificadores aleatorios en cada ejecución.

La ejecución sin argumentos es un dry-run y no conecta con la base de datos:

```bash
python -m scripts.provision_support_admin_client
```

Para aplicar, el comando exige confirmar el nombre exacto de la base de datos Auth.
Además, bloquea explícitamente los entornos `prod` y `production`:

```bash
OSAP_SUPPORT_ADMIN_CLIENT_ID=<UUID>
OSAP_SUPPORT_ADMIN_CLIENT_SECRET=<secreto>
python -m scripts.provision_support_admin_client --apply --confirm-database <nombre-bd-dev>
```

La operación es un UPSERT por UUID: repetirla reconcilia scopes, audiencia, habilitación
y hash del secreto sin crear clientes duplicados. No guardar el secreto en Git ni en logs.
