from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, UploadFile

from .config import Settings, get_settings
from .graph import BimGraph
from .ifc_parser import parse_ifc, resolve_ifc_path
from .lightrag import LightRagClient
from .models import AskRequest, GraphQueryRequest, IngestRequest
from .qa import ask_bim


def require_api_key(
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def get_graph(settings: Settings) -> BimGraph:
    return BimGraph(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)


def get_lightrag(settings: Settings) -> LightRagClient:
    return LightRagClient(settings.lightrag_base_url, settings.lightrag_api_key, settings.lightrag_mode)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    graph = get_graph(settings)
    graph.ensure_schema()
    graph.close()
    yield


app = FastAPI(title="BIM Ingest Service", version="0.1.0", lifespan=lifespan)

JOBS: dict[str, dict] = {}
JOBS_LOCK = Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def set_job(job_id: str, **updates) -> None:
    with JOBS_LOCK:
        current = JOBS.setdefault(job_id, {})
        current.update(updates)
        current["updated_at"] = now_iso()


def run_ingest_job(job_id: str, project_id: str, request_path: str, replace: bool, settings: Settings) -> None:
    set_job(job_id, status="running", message="Parsing IFC and writing Neo4j graph")
    path = resolve_ifc_path(request_path, settings.workspace_prefix, settings.workspace_mount)
    graph = None
    try:
        parsed = parse_ifc(path, project_id)
        graph = get_graph(settings)
        counts = graph.ingest(project_id, parsed, replace)

        lightrag = get_lightrag(settings)
        lightrag_result = asyncio.run(lightrag.ingest_chunks(project_id, parsed.chunks))
        set_job(
            job_id,
            status="completed",
            message="BIM model ingested successfully",
            result={
                "ok": True,
                "project_id": project_id,
                "path": str(path),
                "counts": counts,
                "warnings": parsed.warnings,
                "lightrag": lightrag_result,
            },
        )
    except Exception as exc:
        set_job(job_id, status="failed", message=str(exc), error=str(exc))
    finally:
        if graph is not None:
            graph.close()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"ok": "true"}


@app.post("/projects/{project_id}/ingest", dependencies=[Depends(require_api_key)])
async def ingest_project(
    project_id: str,
    request: IngestRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    path = resolve_ifc_path(request.path, settings.workspace_prefix, settings.workspace_mount)
    try:
        parsed = parse_ifc(path, project_id)
        graph = get_graph(settings)
        counts = graph.ingest(project_id, parsed, request.replace)
        graph.close()

        lightrag = get_lightrag(settings)
        lightrag_result = await lightrag.ingest_chunks(project_id, parsed.chunks)
        return {
            "ok": True,
            "project_id": project_id,
            "path": str(path),
            "counts": counts,
            "warnings": parsed.warnings,
            "lightrag": lightrag_result,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/projects/{project_id}/ingest-jobs", dependencies=[Depends(require_api_key)])
def create_ingest_job(
    project_id: str,
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    job_id = uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "project_id": project_id,
            "status": "queued",
            "message": "Queued for BIM ingestion",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
    background_tasks.add_task(run_ingest_job, job_id, project_id, request.path, request.replace, settings)
    return {"ok": True, "job_id": job_id, "project_id": project_id, "status": "queued"}


@app.get("/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def get_job(job_id: str) -> dict:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"ok": True, **job}


@app.post("/projects/{project_id}/upload", dependencies=[Depends(require_api_key)])
async def upload_project_file(project_id: str, file: UploadFile) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".ifc", ".ifczip"}:
        raise HTTPException(status_code=400, detail="Only .ifc and .ifczip uploads are supported")
    target_dir = Path("/data/uploads") / project_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (file.filename or f"{project_id}{suffix}")
    with target.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            out.write(chunk)
    return {"ok": True, "path": str(target)}


@app.post("/projects/{project_id}/ask", dependencies=[Depends(require_api_key)])
async def ask_project(
    project_id: str,
    request: AskRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    try:
        graph = get_graph(settings)
        lightrag = get_lightrag(settings)
        result = await ask_bim(graph, lightrag, project_id, request.question, request.top_k)
        graph.close()
        return {"ok": True, "project_id": project_id, **result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/projects/{project_id}/graph/query", dependencies=[Depends(require_api_key)])
def graph_query(
    project_id: str,
    request: GraphQueryRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    try:
        graph = get_graph(settings)
        result = graph.run_intent(project_id, request)
        graph.close()
        return {"ok": True, "project_id": project_id, **result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/projects/{project_id}/elements/{global_id}", dependencies=[Depends(require_api_key)])
def get_element(project_id: str, global_id: str, settings: Annotated[Settings, Depends(get_settings)]) -> dict:
    graph = get_graph(settings)
    result = graph.get_element(project_id, global_id)
    graph.close()
    if not result:
        raise HTTPException(status_code=404, detail="Element not found")
    return {"ok": True, "project_id": project_id, "result": result}


@app.get("/projects/{project_id}/spaces", dependencies=[Depends(require_api_key)])
def list_spaces(
    project_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    storey: str | None = None,
    limit: int = 200,
) -> dict:
    graph = get_graph(settings)
    result = graph.list_spaces(project_id, storey, min(max(limit, 1), 500))
    graph.close()
    return {"ok": True, "project_id": project_id, "result": result}
