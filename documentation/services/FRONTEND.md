# Frontend

## Purpose

The frontend is a Vue 3 application built with Vite. It is the part of the Document Management Integration System (DMIS) that users interact with directly in the browser.

It handles things such as:

- User login flow and session-aware navigation.
- Managing external source system connections
- Search flow
- Present document's metadata
- Provides summaries and similarity analysis of documents
- Merging of similar documents
- Sending requests to backend services through the DMIS API gateway

The frontend mainly focuses on the user interface and user interaction. Most business logic, authentication checks, and communication with external systems are handled by backend services instead.

For the definition of a "Document", see [SYSTEM_DOCUMENTATION.md](../SYSTEM_DOCUMENTATION.md).

## Technologies used

The frontend is built using:

- Vue 3
- Vite
- Vue Router
- Nginx
- ESLint and Prettier
- Vitest

## Structure

Frontend structure:

```text
src/
├── assets/       # Static assets
├── components/   # Reusable Vue components
├── composables/  # Reusable Vue composition logic
├── layouts/      # Page layouts
├── router/       # Route configuration and guards
├── test/         # Frontend tests
├── utils/        # API/auth helpers and utilities
└── views/        # Route level pages
```

## Configuration

### Runtime environment variables

The front end uses runtime injected variables through `window.__ENV__` which is generated as `env.js` when the container starts.

- **FRONTEND_DMISAPI_BASE_URL**: Base API path used by the browser, `/api`.
- **FRONTEND_AD_URL**: Identity provider URL used for authentication.
- **FRONTEND_AD_REALM**: Realm/tenant used for OIDC login.
- **FRONTEND_AD_CLIENT_ID**: OIDC client id for the front end.
- **FRONTEND_DMISAPI_URL**: Internal backend URL used by the Nginx reverse proxy.

## Behaviour

### Authentication flow 
Frontend uses OIDC with PKCE for login.

1. User accesses the login page.
2. PKCE verifier and OIDC state are generated.
3. User is redirected to the identity provider.
4. After login, the provider redirects back to `/auth/callback`.
5. The frontend exchanges the returned code through the DMIS API `/auth/codeExchange`.
6. Backend stores authentication cookies.
7. On success, user is routed to the application's `/search`.

**NOTE:** The frontend itself does not validate tokens directly.

#
### Session handling

The authentication is more cookie based and not storing bearer tokens in JavaScript.

- Requests use `credentials: include`.
- Failed requests with `401` trigger a refresh attempt through `/auth/refresh`.
- Logout calls `/auth/logout` and are synchronized between tabs via `localStorage`.

#
### Routes

- **Public routes**
  - `/` (login)
  - `/auth/callback`
  - `/session/callback`
- **Authenticated routes**
  - `/connections`
  - `/search`
  - `/merge-files`
- **Admin-only routes**
  - `/sources`
  - `/intelligence`
  - `/compliance`
  - `/settings`

Access checks are performed through backend authentication endpoints before navigation is allowed. Users without access are redirected to an error page.

#
### API usage

The frontend calls backend services through the DMIS API gateway.

**Endpoints:**

- **Search engine**
  - `/search_engine/search`
  - `/search_engine/find_matching`
  - `/search_engine/classifications`
  - `/search_engine/classification`
  - `/search_engine/file_types`
  - `/search_engine/file_types_documents_only`
- **Stochastic analyzer**
  - `/stochastic-analyzer/summarize`
  - `/stochastic-analyzer/merge`
  - `/stochastic-analyzer/md-to-pdf`
- **Connector services**
  - `/connector/connected_source_systems`
  - `/connector/get_auth_user_urls`
  - `/connector/auth_user`
  - `/connector/active-sessions`
  - `/connector/session-callback`
- **Authentication**
  - `/auth/check`
  - `/auth/me`
  - `/auth/refresh`
  - `/auth/logout`
  - `/auth/codeExchange`
  - `/auth/checkAdmin`
  