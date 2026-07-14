# Workspace SSO

This stack uses Keycloak as the identity provider and oauth2-proxy as the shared
login gate for the workspace apps.

## Public hostnames

Cloudflare Tunnel currently uses a remote configuration with these origins:

- `app.hiep265.shop` -> `http://app-shell:3000`
- `chat.hiep265.shop` -> `http://chatwoot-web:3000`
- `post.hiep265.shop` -> `http://postiz-web:5000`
- `openclaw.hiep265.shop` -> `http://openclaw-gateway:18789`

The compose file puts `cloudflared` on a separate `edge-network` where those
origin names are aliases for `nginx-proxy`. Nginx then enforces SSO and proxies
to the real app containers through `*-origin` aliases on `workspace-network`.

## Login flow

1. A user opens `https://app.hiep265.shop`, `https://chat.hiep265.shop`,
   `https://post.hiep265.shop`, or `https://openclaw.hiep265.shop`.
2. Nginx asks oauth2-proxy whether the request has a valid `_workspace_sso`
   session.
3. If the user is not logged in, oauth2-proxy redirects to
   `https://app.hiep265.shop/realms/workspace`.
4. After login, the shared `.hiep265.shop` cookie lets the user enter all
   protected apps without another gateway login.

## Bootstrap accounts

Keycloak admin console:

- URL: `https://app.hiep265.shop/admin/`
- Username: `workspace-admin`
- Password: `b6a474783e5c0c5ef0f3202ab10aeb4dc0639287b004aa17`

Imported workspace user:

- URL: `https://app.hiep265.shop/realms/workspace/account/`
- Username: `owner`
- Email: `owner@hiep265.shop`
- Temporary password: `ChangeMe_SSO_2026!`

Change both passwords before using this outside a private test environment.

## App-specific notes

Postiz is configured to use the `postiz` OIDC client in Keycloak via generic
OAuth. The wrapper starts Postiz SSO from:

```text
https://app.hiep265.shop/api/postiz-sso
```

The OIDC redirect URIs are:

```text
https://post.hiep265.shop/settings
https://post.hiep265.shop/auth*
```

The `owner@hiep265.shop` user is pre-provisioned in Postiz with provider
`GENERIC`, so Keycloak SSO can create the Postiz app session without showing the
sign-up form.

Chatwoot is protected by the shared SSO gate and has native account-level SAML
configured against Keycloak for account `1`.

- Entry URL: `https://chat.hiep265.shop/`
- SAML start URL: `https://chat.hiep265.shop/auth/saml?account_id=1&RelayState=web`
- SP entity ID: `https://chat.hiep265.shop/saml/sp/1`
- IdP SSO URL: `https://app.hiep265.shop/realms/workspace/protocol/saml`

Opening the Chatwoot entry URL redirects to the SAML start URL. If the user does
not have the shared `_workspace_sso` cookie yet, the gateway first sends them to
Keycloak OIDC login; once that session exists, Chatwoot's SAML flow reuses the
same Keycloak login.

OpenClaw uses `trusted-proxy` auth. Nginx first validates the shared
`_workspace_sso` cookie through oauth2-proxy, then forwards the authenticated
email in `X-Auth-Request-Email` to OpenClaw. Users should open:

```text
https://openclaw.hiep265.shop/
```
