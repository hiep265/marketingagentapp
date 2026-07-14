import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const BIM_SERVICE_URL = process.env.BIM_SERVICE_URL || 'http://bim-ingest-service:8095';
const BIM_SERVICE_API_KEY = process.env.BIM_SERVICE_API_KEY || 'bim-dev-key';

export async function POST(request) {
  try {
    const body = await request.json();
    const projectId = String(body.project_id || '').trim();
    const question = String(body.question || '').trim();

    if (!projectId || !question) {
      return NextResponse.json({ ok: false, error: 'project_id and question are required' }, { status: 400 });
    }

    const res = await fetch(`${BIM_SERVICE_URL}/projects/${encodeURIComponent(projectId)}/ask`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': BIM_SERVICE_API_KEY
      },
      body: JSON.stringify({ question, top_k: Number(body.top_k || 8) })
    });

    const result = await res.json().catch(() => ({}));
    return NextResponse.json(result, { status: res.status });
  } catch (err) {
    return NextResponse.json({ ok: false, error: err instanceof Error ? err.message : String(err) }, { status: 500 });
  }
}
