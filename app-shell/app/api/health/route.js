import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

async function checkService(url, timeoutMs = 1500) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: { 'User-Agent': 'Workspace-Healthcheck' }
    });
    clearTimeout(id);
    return res.ok || res.status < 500; // 2xx/3xx/4xx are considered online, 5xx or offline is dead
  } catch (err) {
    clearTimeout(id);
    return false;
  }
}

export async function GET() {
  // Check internal Docker service endpoints
  const chatwootOnline = await checkService('http://chatwoot-web:3000/');
  const postizOnline = await checkService('http://postiz-web:5000/');
  const openclawOnline = await checkService('http://openclaw-gateway:18789/healthz');
  const bimOnline = await checkService('http://bim-ingest-service:8095/healthz');

  return NextResponse.json({
    chatwoot: chatwootOnline ? 'online' : 'offline',
    postiz: postizOnline ? 'online' : 'offline',
    openclaw: openclawOnline ? 'online' : 'offline',
    bim: bimOnline ? 'online' : 'offline',
    timestamp: new Date().toISOString()
  });
}
