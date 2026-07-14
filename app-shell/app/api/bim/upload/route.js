import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const BIM_SERVICE_URL = process.env.BIM_SERVICE_URL || 'http://bim-ingest-service:8095';
const BIM_SERVICE_API_KEY = process.env.BIM_SERVICE_API_KEY || 'bim-dev-key';

function cleanProjectId(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export async function POST(request) {
  try {
    const form = await request.formData();
    const file = form.get('file');
    const projectId = cleanProjectId(form.get('project_id'));
    const replace = form.get('replace') !== 'false';

    if (!projectId) {
      return NextResponse.json({ ok: false, error: 'project_id is required' }, { status: 400 });
    }

    if (!file || typeof file.name !== 'string') {
      return NextResponse.json({ ok: false, error: 'IFC file is required' }, { status: 400 });
    }

    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith('.ifc') && !lowerName.endsWith('.ifczip')) {
      return NextResponse.json({ ok: false, error: 'Only .ifc and .ifczip files are supported' }, { status: 400 });
    }

    const uploadForm = new FormData();
    uploadForm.set('file', file, file.name);

    const uploadRes = await fetch(`${BIM_SERVICE_URL}/projects/${encodeURIComponent(projectId)}/upload`, {
      method: 'POST',
      headers: { 'x-api-key': BIM_SERVICE_API_KEY },
      body: uploadForm
    });

    const uploadBody = await uploadRes.json().catch(() => ({}));
    if (!uploadRes.ok) {
      return NextResponse.json({ ok: false, error: uploadBody.detail || 'Upload failed' }, { status: uploadRes.status });
    }

    const ingestRes = await fetch(`${BIM_SERVICE_URL}/projects/${encodeURIComponent(projectId)}/ingest-jobs`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': BIM_SERVICE_API_KEY
      },
      body: JSON.stringify({ path: uploadBody.path, replace })
    });

    const ingestBody = await ingestRes.json().catch(() => ({}));
    if (!ingestRes.ok) {
      return NextResponse.json({ ok: false, error: ingestBody.detail || 'Ingest failed', upload: uploadBody }, { status: ingestRes.status });
    }

    return NextResponse.json({ ok: true, upload: uploadBody, ingestJob: ingestBody });
  } catch (err) {
    return NextResponse.json({ ok: false, error: err instanceof Error ? err.message : String(err) }, { status: 500 });
  }
}
