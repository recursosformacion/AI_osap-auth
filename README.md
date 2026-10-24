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
