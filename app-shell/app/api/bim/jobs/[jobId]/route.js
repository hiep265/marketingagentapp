import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const BIM_SERVICE_URL = process.env.BIM_SERVICE_URL || 'http://bim-ingest-service:8095';
const BIM_SERVICE_API_KEY = process.env.BIM_SERVICE_API_KEY || 'bim-dev-key';

export async function GET(_request, { params }) {
  try {
    const { jobId } = await params;
    const res = await fetch(`${BIM_SERVICE_URL}/jobs/${encodeURIComponent(jobId)}`, {
      headers: { 'x-api-key': BIM_SERVICE_API_KEY }
    });
    const result = await res.json().catch(() => ({}));
    return NextResponse.json(result, { status: res.status });
  } catch (err) {
    return NextResponse.json({ ok: false, error: err instanceof Error ? err.message : String(err) }, { status: 500 });
  }
}
