# BIM Ingest Service

FastAPI service for IFC / IFCZIP ingestion, deterministic BIM graph storage in Neo4j, and optional LightRAG ingestion/query.

## API

- `POST /projects/{project_id}/ingest` with `{ "path": "/workspace/model.ifc", "replace": true }`
- `POST /projects/{project_id}/upload` multipart upload for `.ifc` or `.ifczip`
- `POST /projects/{project_id}/ask` with `{ "question": "Tầng 3 có bao nhiêu cửa?", "top_k": 8 }`
- `POST /projects/{project_id}/graph/query`
- `GET /projects/{project_id}/elements/{global_id}`
- `GET /projects/{project_id}/spaces?storey=3`

All protected endpoints require `x-api-key`.

## Notes

The graph written to Neo4j is deterministic from IFC relationships and properties. LightRAG is optional and used for semantic summaries or open-ended questions.
