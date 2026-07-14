import { headers } from 'next/headers';
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  const requestHeaders = await headers();

  return NextResponse.json({
    user:
      requestHeaders.get('x-auth-request-user') ||
      requestHeaders.get('x-forwarded-user') ||
      null,
    email:
      requestHeaders.get('x-auth-request-email') ||
      requestHeaders.get('x-forwarded-email') ||
      null,
    groups: requestHeaders.get('x-auth-request-groups') || null,
  });
}
