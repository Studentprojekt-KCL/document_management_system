# DMIS API

## Configuration

### Environment variables

- **DMISAPI_BIND_PORT**: Which port to bind to.
- **DMISAPI_BIND_ADDR**: Which address to bind to.
- **DMISAPI_SEARCHENG_URL**: Search engine url.
- **DMISAPI_STOCHAN_URL**: Stochastic analyzer url.
- **DMISAPI_CONGATEWAY_URL**: Connector gateway url.
- **DMISAPI_AD_URL**: Identity provider issuer url.
- **DMISAPI_AD_JWKS_URL**: JWKS endpoint used to verify access tokens.
- **DMISAPI_AD_ALLOWED_AZP**: Allowed `azp` claim values, comma separated if multiple.
- **DMISAPI_AD_TOKEN_URL**: Identity provider token endpoint.
- **DMISAPI_AD_LOGOUT_URL**: Identity provider logout endpoint.
- **DMISAPI_AD_CLIENT_ID**: Client id used for auth and role lookup.
- **DMISAPI_AD_AUDIENCE**: Expected `aud` claim values, comma separated if multiple. Optional.
- **DMISAPI_SEARCHENG_SCOPE**: Required scope names for search engine proxy routes, space separated if multiple. Optional.
- **DMISAPI_STOCHAN_SCOPE**: Required scope names for stochastic analyzer proxy routes, space separated if multiple. Optional.
- **DMISAPI_CONGATEWAY_SCOPE**: Required scope names for connector proxy routes, space separated if multiple. Optional.
- **DMISAPI_ADMIN_ROLES**: Client roles that should be treated as admin roles, comma separated if multiple. Optional.
- **LOGAPI_URL**: Logger url. In deployment this is commonly mapped from `DMISAPI_LOGAPI_URL`.

### Flags

- `--dev`: Enable dev prints.

## Behaviour

The API acts as a thin authenticated gateway in front of the search engine, stochastic analyzer and connector gateway.

All proxied service routes expect the user access token to be present in the `access_token` cookie. The token is validated against the configured issuer and JWKS endpoint. If `DMISAPI_AD_AUDIENCE` is set, the audience claim is enforced. If `DMISAPI_AD_ALLOWED_AZP` is set, the `azp` claim must match one of the configured values.

Per-upstream scope requirements can be enabled through `DMISAPI_SEARCHENG_SCOPE`, `DMISAPI_STOCHAN_SCOPE` and `DMISAPI_CONGATEWAY_SCOPE`. If any of these are set, the token must contain all listed scopes before the request is forwarded.

The API forwards query parameters, JSON request bodies and the resolved bearer token to the upstream service. Connector GET requests also forward the incoming `Referer` header and, if present, the `x-connector-authorization` header.

Authentication routes handle the login session. `codeExchange` exchanges an authorization code for tokens and stores them in secure HTTP-only cookies. `refresh` refreshes the session using the `refresh_token` cookie. `logout` clears the local cookies and returns an identity-provider logout url for the frontend to redirect the user to.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
|`/search_engine/{endpoint}`|GET|Forward a GET request to the search engine.|
|`/search_engine/{endpoint}`|POST|Forward a POST request to the search engine.|
|`/stochastic-analyzer/{endpoint}`|GET|Forward a GET request to the stochastic analyzer.|
|`/stochastic-analyzer/{endpoint}`|POST|Forward a POST request to the stochastic analyzer.|
|`/connector/{endpoint}`|GET|Forward a GET request to the connector gateway.|
|`/connector/{endpoint}`|POST|Forward a POST request to the connector gateway.|
|`/auth/codeExchange`|POST|Exchange an authorization code for session cookies.|
|`/auth/check`|GET|Check whether the current session is authenticated.|
|`/auth/checkAdmin`|GET|Check whether the current session has an admin role.|
|`/auth/me`|GET|Get information about the authenticated user.|
|`/auth/refresh`|POST|Refresh the current session.|
|`/auth/logout`|POST|Clear local auth cookies and return logout redirect url.|

### Search Engine Proxy

Forward a request to the search engine using the same path segment after `/search_engine/`.

*Cookies*

- `access_token`: Access token used as bearer token to the search engine.

*Params*

- Same query parameters as the target search engine endpoint.

*Body*

- Same JSON body as the target search engine endpoint for POST requests.

*Response*

- Same response body and content type as the target search engine endpoint.

### Stochastic Analyzer Proxy

Forward a request to the stochastic analyzer using the same path segment after `/stochastic-analyzer/`.

*Cookies*

- `access_token`: Access token used as bearer token to the stochastic analyzer.

*Params*

- Same query parameters as the target stochastic analyzer endpoint.

*Body*

- Same JSON body as the target stochastic analyzer endpoint for POST requests.

*Response*

- Same response body and content type as the target stochastic analyzer endpoint.

### Connector Proxy

Forward a request to the connector gateway using the same path segment after `/connector/`.

*Cookies*

- `access_token`: Access token used as bearer token to the connector gateway.

*Headers*

- `x-connector-authorization`: Optional connector-specific credential forwarded on GET requests.
- `referer`: Forwarded on GET requests when present.

*Params*

- Same query parameters as the target connector endpoint.

*Body*

- Same JSON body as the target connector endpoint for POST requests.

*Response*

- Same response body and content type as the target connector endpoint.

### Code Exchange

Exchange the authorization code from the identity provider for session cookies.

*Headers*

- `origin`: Used to construct the redirect uri `<origin>/auth/callback`.

*Body*

Sent as form data.

```json
{
    "code": <STRING>,
    "code_verifier": <STRING>
}
```

*Response*

```json
{
    "message": "Login successful"
}
```

### Check

Check whether the current user is authenticated and has at least one client role for `DMISAPI_AD_CLIENT_ID`.

*Cookies*

- `access_token`: Access token cookie.

*Response*

```json
{
    "authenticated": true,
    "user": {
        "username": <STRING>
    }
}
```

### Check Admin

Check whether the current user has one of the configured admin roles.

*Cookies*

- `access_token`: Access token cookie.

*Response*

```json
{
    "admin": <BOOLEAN>
}
```

### Me

Get information about the authenticated user and the roles found in the access token.

*Cookies*

- `access_token`: Access token cookie.

*Response*

```json
{
    "authenticated": true,
    "user": {
        "username": <STRING>,
        "email": <STRING>,
        "client_roles": [
            <STRING>,
            <STRING>
        ],
        "realm_roles": [
            <STRING>,
            <STRING>
        ]
    }
}
```

### Refresh

Refresh the session using the refresh token cookie.

*Cookies*

- `refresh_token`: Refresh token cookie.

*Response*

```json
{
    "message": "Session refreshed"
}
```

### Logout

Clear the local authentication cookies and return the identity-provider logout url.

*Headers*

- `origin`: Used to construct the `post_logout_redirect_uri`.

*Cookies*

- `id_token`: Optional id token cookie, forwarded as `id_token_hint` when present.

*Response*

```json
{
    "logout_url": <STRING>
}
```
