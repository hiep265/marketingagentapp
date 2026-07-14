const KEYCLOAK_AUTH_URL = 'https://app.hiep265.shop/realms/workspace/protocol/openid-connect/auth';
const POSTIZ_CALLBACK_URL = 'https://post.hiep265.shop/auth?provider=GENERIC';

export async function GET() {
  const params = new URLSearchParams({
    client_id: 'postiz',
    scope: 'openid profile email',
    response_type: 'code',
    redirect_uri: POSTIZ_CALLBACK_URL,
  });

  return Response.redirect(`${KEYCLOAK_AUTH_URL}?${params.toString()}`, 302);
}
