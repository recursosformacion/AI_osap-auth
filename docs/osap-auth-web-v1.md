# OSAP Auth Web v1.0

**Estado:** implementado (frontend de `osap-auth`).
**Stack:** React 18 + TypeScript + Vite + React Router + Vitest/Testing Library.
**Ubicación:** `osap-auth/web/`.

---

# 1. Objetivo

Aplicación web independiente de autenticación de OSAP. Consume **exclusivamente** la API
pública de osap-auth (`osap-auth-api-v1.0`) y **nunca** accede a la base de datos ni a otra
aplicación OSAP. Está preparada para integrarse posteriormente bajo `/auth/*` en las apps OSAP.

---

# 2. Estructura

```
osap-auth/web/
├── public/
├── src/
│   ├── api/            # httpClient (refresh/retry), authApi, types
│   ├── auth/           # AuthContext, authStorage, authTypes
│   ├── components/     # AuthLayout, FormField, PasswordField, Loading, ErrorMessage, AccountLayout
│   ├── pages/          # Login, Register, VerifyEmail, ForgotPassword, ResetPassword,
│   │                   #   Account, Sessions, ChangePassword, ChangeEmail, DeleteAccount, Logout, AdminUsers
│   ├── routes/         # ProtectedRoute, AdminRoute
│   ├── hooks/          # useSubmission
│   ├── utils/          # validation
│   ├── styles/         # global.css (design tokens + estilos)
│   ├── App.tsx
│   └── main.tsx
├── tests/              # suites Vitest + Testing Library
├── .env.example / .env.development / .env.production
├── package.json / vite.config.ts / tsconfig.json / eslint.config.js
```

Separación conceptual: `api` (comunicación), `auth` (estado de sesión), `components`/`pages`
(UI), `routes` (guards). No se construyen llamadas HTTP desde componentes: todo pasa por
`authApi`.

---

# 3. Configuración

La URL del backend **nunca** está hardcodeada en componentes. Se lee de:

```env
VITE_AUTH_API_URL=http://127.0.0.1:8200
```

Preparados: `.env.development` (local) y `.env.production` (producción, sin URL definitiva
todavía).

---

# 4. Cliente API (`src/api/httpClient.ts`)

Único cliente HTTP con:

- URL base desde `VITE_AUTH_API_URL`.
- Cabeceras JSON + `Authorization: Bearer` cuando hay access token.
- **Refresh automático**: ante un `401`, renueva con el refresh token (una vez, con
  `Promise` compartida para no duplicar renovaciones) y reintenta la petición.
- Si el refresh falla, limpia la sesión y notifica al `AuthContext` (logout forzado).
- Errores normalizados con `status` + `message` (mensaje `detail` del backend).

`src/api/authApi.ts` agrupa las llamadas: `register`, `verifyEmail`, `resendVerification`,
`login`, `refresh`, `logout`, `logoutAll`, `getSessions`, `revokeSession`, `getMe`,
`changePassword`, `requestPasswordReset`, `confirmPasswordReset`, `changeEmail`,
`confirmChangeEmail`, `deleteAccount`, `adminListUsers`.

---

# 5. Gestión de sesión (`src/auth/`)

- **`authStorage`**: guarda access token, refresh token y una sesión **mínima sin PII**
  (`user_id`, `roles`, `email_verified`). No se persiste el email.
- **`AuthContext`**: estados `anonymous | authenticated | loading`. Expone `user`,
  `isAuthenticated`, `isLoading`, `isAdmin`, `login()`, `logout()`, `refresh()`.
- **Restauración al recargar**: si hay access token, `getMe()` restaura el usuario.

---

# 6. Rutas

| Ruta | Acceso | Página |
|------|--------|--------|
| `/auth/login` | pública | Login |
| `/auth/register` | pública | Registro |
| `/auth/verify-email` | pública | Verificación (token en query) |
| `/auth/forgot-password` | pública | Recuperar contraseña |
| `/auth/reset-password` | pública | Nueva contraseña (token en query) |
| `/auth/logout` | pública | Cerrar sesión |
| `/auth/account` | protegida | Cuenta |
| `/auth/account/sessions` | protegida | Sesiones |
| `/auth/account/password` | protegida | Cambiar contraseña |
| `/auth/account/email` | protegida | Cambiar email |
| `/auth/account/delete` | protegida | Eliminar cuenta |
| `/auth/admin/users` | rol `admin` | Administración de usuarios |

`ProtectedRoute` exige sesión; `AdminRoute` exige rol `admin` **según los datos del
backend** (claim `roles`), sin lógica de autorización paralela en el frontend.

---

# 7. Diseño

`src/styles/global.css` con tokens de diseño (color, sombra, radios) y clases compartidas.
Transmite seguridad y simplicidad: tarjeta centrada, marca OSAP, mensajes de estado claros,
responsive (escritorio / tablet / móvil). No usa frameworks de UI.

---

# 8. Seguridad

- No se almacenan contraseñas ni refresh token en claro visible.
- No se escriben tokens en logs ni se muestran datos sensibles en errores.
- No hay PII (email) en el almacenamiento del token ni en la sesión persistida.
- Los contenidos del backend se renderizan como texto (React escapa por defecto → anti-XSS).
- El registro y la recuperación de contraseña muestran mensajes genéricos, sin revelar si
  el email existe (acorde al contrato).

---

# 9. Tests

`tests/` (Vitest + Testing Library), 19 casos: validación, AuthContext (restauración, sin
PII), httpClient (refresh/retry, logout forzado, mensajes de error), Login, Register,
VerifyEmail (éxito, inválido, ya verificado, sin token), ProtectedRoute (redirección y
acceso). Comandos:

```powershell
npm run typecheck   # tsc --noEmit
npm run lint        # eslint src
npm test            # vitest run
npm run build       # tsc --noEmit && vite build
```

---

# 10. Endpoints backend utilizados

`POST /auth/register`, `POST /auth/verify-email`, `POST /auth/resend-verification`,
`POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/logout-all`,
`GET /auth/sessions`, `DELETE /auth/sessions/{id}`, `GET /auth/me`,
`POST /auth/me/password`, `POST /auth/me/email`, `POST /auth/change-email/confirm`,
`POST /auth/password-reset/request`, `POST /auth/password-reset/confirm`,
`DELETE /auth/me`, `GET /auth/admin/users`.

Ningún endpoint administrativo inexistente se ha inventado: el listado de administración usa
`GET /auth/admin/users` existente; la búsqueda en servidor, filtros avanzados, cambio de rol,
activación/desactivación y sesiones por usuario **no existen aún** y quedan documentados como
pendientes en la propia página.

---
*Documentación de OSAP Auth Web v1.0 (2026-08).*
