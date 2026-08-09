# Prompt de implementación — OSAP Auth v1.0

**Versión:** 1.0
**Estado:** contrato congelado — listo para implementación

## 1. Rol

Eres un ingeniero implementando OSAP Auth v1.0, un servicio independiente de identidad y autenticación.

OSAP Auth debe funcionar como un servicio autónomo, con su propio código, configuración, base de datos, migraciones y mecanismos de seguridad.

### Regla crítica

Los contratos de OSAP Auth están congelados.

**NO debes:**

- reinterpretar la arquitectura;
- modificar el contrato;
- añadir funcionalidades no especificadas;
- introducir dependencias con otros servicios;
- compartir tablas o modelos de base de datos con otros sistemas;
- asumir estructuras de datos externas;
- acceder directamente a bases de datos ajenas.

Tu trabajo consiste en implementar exactamente el contrato definido en:

```
docs/osap-auth-api-v1.0.md
```

El documento de propuesta:

```
docs/osap-auth-proposal-v1.md
```

es únicamente histórico y de contexto. Si existe cualquier discrepancia, prevalece siempre el contrato v1.0.

---

## 2. Independencia de OSAP Auth

OSAP Auth es propietario de toda la información relacionada con identidad y autenticación.

Debe disponer de:

- su propia base de datos;
- sus propias migraciones;
- sus propios modelos;
- sus propias tablas;
- sus propios repositorios;
- sus propias claves criptográficas;
- sus propias sesiones;
- sus propios mecanismos de auditoría;
- su propia configuración.

No utilizar una base de datos compartida.

No crear tablas en bases de datos externas.

No importar modelos de persistencia de otros servicios.

No consultar directamente ninguna base de datos externa.

La única información que puede salir de OSAP Auth es la contemplada por su API y sus mecanismos estándar de autenticación.

---

## 3. Base de datos

La base de datos de OSAP Auth será exclusiva del servicio.

**Stack obligatorio:**

- MySQL
- aiomysql
- SQLAlchemy async, si ya forma parte del stack elegido
- migraciones mediante Alembic
- acceso exclusivamente desde `infrastructure`

La estructura deberá permitir evolucionar el servicio sin afectar a ningún otro componente.

Como mínimo deberán existir las estructuras necesarias para:

- usuarios;
- sesiones;
- refresh tokens;
- tokens de verificación;
- tokens de recuperación;
- clientes de servicio;
- claves/versiones criptográficas;
- auditoría;
- rate limiting.

El agente deberá consultar el contrato para determinar los campos exactos.

---

## 4. Stack tecnológico

**Obligatorio:**

- Python 3.11+
- FastAPI
- Pydantic v2
- pydantic-settings
- MySQL
- aiomysql
- Argon2id
- JWT
- JWKS
- AES-256-GCM
- HMAC-SHA256
- pytest
- pytest-asyncio
- ruff
- mypy

**Arquitectura:**

```
domain/
application/
infrastructure/
api/
```

Mantener separación clara entre:

- dominio;
- casos de uso;
- persistencia;
- criptografía;
- infraestructura;
- API HTTP.

---

## 5. Modelo de identidad

El identificador principal será:

```
user_id = UUID
```

Debe ser:

- opaco;
- permanente mientras exista la cuenta;
- generado por OSAP Auth;
- independiente del email;
- independiente del nombre;
- independiente de cualquier identificador externo.

El email no es el identificador del usuario.

---

## 6. Protección del email

No almacenar el email en claro.

Utilizar:

**`email_lookup`** — HMAC-SHA256 normalizado:

```
HMAC-SHA256(email_normalizado, pepper)
```

Su única finalidad es localizar una cuenta.

**`email_cipher`** — AES-256-GCM.

Su única finalidad es recuperar el email para operaciones que necesiten mostrarlo.

- Nunca utilizar `email_cipher` para búsquedas.
- Nunca utilizar `email_lookup` para mostrar el email.

---

## 7. Contraseñas y tokens

Las contraseñas deberán almacenarse exclusivamente mediante:

```
Argon2id
```

Los tokens sensibles deberán almacenarse exclusivamente mediante hash.

Nunca guardar en base de datos:

- contraseña en claro;
- refresh token en claro;
- verification token en claro;
- reset token en claro.

---

## 8. Registro

Implementar:

```
POST /auth/register
```

El registro deberá:

- normalizar el email;
- generar `user_id`;
- generar `email_lookup`;
- cifrar el email;
- generar hash Argon2id de la contraseña;
- crear el usuario en estado `pending_verification`;
- generar token de verificación;
- almacenar únicamente el hash del token;
- aplicar expiración y un solo uso;
- respetar las reglas anti-enumeración del contrato.

---

## 9. Verificación de email

Implementar los endpoints definidos en el contrato para:

- verificar email;
- reenviar verificación.

El token debe ser:

- aleatorio;
- de un solo uso;
- temporal;
- almacenado únicamente mediante hash;
- invalidado después de utilizarse.

---

## 10. Login

Implementar:

```
POST /auth/login
```

La búsqueda de usuario se realizará mediante `email_lookup`.

La contraseña se comprobará mediante Argon2id.

El sistema debe evitar revelar:

- si el email existe;
- si la contraseña es incorrecta;
- información interna de la cuenta.

Aplicar las medidas de timing y rate limiting especificadas en el contrato.

---

## 11. Access Token

Emitir JWT firmado.

**Características:**

- TTL: 15 minutos;
- RS256 o ES256;
- validable mediante JWKS;
- `user_id` como `sub`;
- sin PII;
- sin email;
- sin información sensible.

**Claims según contrato:**

```
iss
sub
aud
jti
roles
email_verified
iat
exp
scope
```

---

## 12. JWKS

Implementar:

```
GET /auth/.well-known/jwks.json
```

Las claves privadas nunca deben exponerse.

Preparar el sistema para rotación mediante `kid` y versionado de claves.

---

## 13. Refresh tokens

Implementar refresh tokens opacos.

**Características:**

- nunca JWT;
- almacenados únicamente mediante hash;
- rotación;
- revocación;
- detección de reutilización;
- asociación a sesión;
- expiración.

Si se detecta reutilización según las reglas del contrato:

- revocar las sesiones correspondientes según la política definida.

---

## 14. Sesiones

Persistir las sesiones en la base de datos propia.

Implementar:

- listar sesiones
- revocar sesión
- logout
- logout-all

Las sesiones deben poder ser revocadas individualmente y globalmente según el contrato.

---

## 15. Recuperación de contraseña

Implementar:

- `password-reset/request`
- `password-reset/confirm`
- `POST /auth/me/password`

Los tokens de recuperación:

- serán de un solo uso;
- tendrán expiración;
- se almacenarán únicamente mediante hash;
- no se devolverán posteriormente desde la base de datos.

Al cambiar correctamente la contraseña deberán aplicarse las revocaciones especificadas por el contrato.

---

## 16. Service-to-service authentication

Implementar:

```
POST /oauth/token
```

utilizando:

```
client_credentials
```

Los clientes de servicio deberán ser entidades propias de OSAP Auth.

Sus secretos deberán almacenarse mediante hash.

Implementar los scopes definidos por el contrato.

Los tokens de servicio no deben contener identidad de usuario.

---

## 17. Cifrado y gestión de claves

Implementar:

- AES-256-GCM para información personal cifrada.
- HMAC-SHA256 para valores de búsqueda.

Utilizar:

```
key_version
```

para permitir rotación de claves.

La arquitectura debe permitir evolucionar las claves sin tener que rediseñar la base de datos.

---

## 18. Rate limiting

Implementar rate limiting para las operaciones sensibles indicadas en el contrato.

Como mínimo:

- registro;
- login;
- reenvío de verificación;
- recuperación de contraseña.

Debe evitar tanto:

- abuso;
- fuerza bruta;
- enumeración de usuarios.

---

## 19. Auditoría

Implementar una auditoría propia de OSAP Auth.

Debe ser:

- append-only;
- trazable;
- sin almacenar secretos;
- sin almacenar contraseñas;
- sin almacenar tokens;
- sin introducir PII innecesaria.

Registrar los eventos definidos en el contrato.

---

## 20. Borrado de cuenta

Implementar:

```
DELETE /auth/me
```

siguiendo exactamente la política definida en el contrato.

El proceso deberá contemplar:

- invalidación de sesiones;
- tratamiento de credenciales;
- tratamiento del email;
- retención;
- auditoría;
- estado final de la cuenta.

Emitir el evento:

```
user.deleted
```

según el contrato.

El evento debe utilizar únicamente la información que el contrato permita.

---

## 21. API pública

Implementar todos los endpoints definidos en:

```
docs/osap-auth-api-v1.0.md
```

incluyendo:

- register
- verify-email
- resend-verification
- login
- logout
- logout-all
- refresh
- sessions
- password-reset
- me
- change-password
- change-email
- version
- jwks
- oauth/token

No añadir endpoints fuera del contrato salvo que sean estrictamente necesarios para la implementación interna y no formen parte de la API pública.

---

## 22. Auth ≠ Authorization

OSAP Auth determina exclusivamente:

> ¿Quién es este usuario o cliente?

No debe implementar reglas de negocio.

No debe decidir:

- quién puede votar;
- qué obras puede modificar alguien;
- qué operaciones concretas puede ejecutar un usuario;
- reglas específicas de negocio;
- permisos funcionales de otros servicios.

Los scopes de autenticación son los definidos por el propio contrato de Auth.

---

## 23. Seguridad

Aplicar:

- anti-enumeración;
- rate limiting;
- Argon2id;
- cifrado AEAD;
- rotación de claves;
- expiración de tokens;
- revocación;
- detección de reutilización;
- auditoría;
- validación estricta de JWT;
- validación de `iss`;
- validación de `aud`;
- validación de `exp`;
- validación de `iat`;
- validación de `jti`;
- `kid`/JWKS.

No introducir mecanismos de seguridad no contemplados que alteren el contrato.

---

## 24. GDPR y retención

Implementar las políticas establecidas en el contrato v1.0.

Especial atención a:

- minimización de PII;
- borrado;
- retención;
- auditoría;
- cifrado;
- recuperación;
- anonimización cuando corresponda.

---

## 25. Fuera de alcance

No implementar:

- OAuth social;
- Google/Apple/GitHub login;
- SAML;
- SSO;
- MFA;
- TOTP;
- passkeys;
- recuperación por teléfono;
- notificaciones push;
- multi-tenant;
- ABAC;
- funcionalidades de negocio.

Quedan para versiones posteriores.

---

## 26. Tests

Crear tests unitarios, de integración y API suficientes para demostrar el cumplimiento del contrato.

Como mínimo:

- registro;
- email cifrado;
- búsqueda mediante HMAC;
- verificación;
- expiración de tokens;
- un solo uso;
- login;
- anti-enumeración;
- refresh;
- rotación;
- reuse detection;
- logout;
- logout-all;
- sesiones;
- password reset;
- JWT;
- JWKS;
- scopes;
- service authentication;
- rate limiting;
- auditoría;
- borrado de cuenta;
- GDPR;
- version.

---

## 27. Validación final

Antes de finalizar ejecutar:

```
ruff check .
mypy .
pytest
```

Los tres deben finalizar correctamente.

Además comprobar que:

- las migraciones se ejecutan desde una BD vacía;
- las migraciones son reproducibles;
- el servicio puede arrancar sin ninguna base de datos externa;
- el servicio puede funcionar con su propia configuración;
- no existen imports hacia otros proyectos;
- no existen conexiones a bases de datos externas;
- no existen tablas compartidas;
- no existen dependencias de modelos externos.

---

## 28. Entregables

Entregar:

```
osap-auth/
├── api/
├── application/
├── domain/
├── infrastructure/
├── migrations/
├── tests/
├── docs/
├── configuration...
└── ...
```

Además:

- código completo;
- migraciones;
- configuración necesaria;
- tests;
- documentación técnica;
- documentación de despliegue;
- informe final de implementación.

El informe final debe indicar, punto por punto:

```
Contrato → Implementación → Test → Estado
```

---

## Regla final

OSAP Auth debe poder desarrollarse, probarse, migrarse, desplegarse y evolucionar de forma completamente independiente.

- No asumir ninguna estructura de datos externa.
- No compartir base de datos.
- No compartir modelos de persistencia.
- No introducir dependencias entre proyectos.

La API pública y los mecanismos estándar de autenticación son la única frontera del servicio.

**Implementa el contrato. No lo rediseñes.**
