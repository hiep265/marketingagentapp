from typing import Any, Literal
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    path: str = Field(..., description="Path to .ifc or .ifczip visible to the service")
    replace: bool = True


class AskRequest(BaseModel):
    question: str
    top_k: int = Field(default=8, ge=1, le=30)


class GraphQueryRequest(BaseModel):
    intent: Literal[
        "node_types",
        "count_entities",
        "list_entities",
        "count_elements",
        "list_elements",
        "list_spaces",
        "get_element",
        "property_search",
    ]
    label: str | None = None
    class_name: str | None = None
    name: str | None = None
    storey: str | None = None
    space: str | None = None
    global_id: str | None = None
    property_name: str | None = None
    property_value: str | None = None
    limit: int = Field(default=50, ge=1, le=500)


class BimNode(BaseModel):
    id: str
    label: str
    props: dict[str, Any]


class BimRelation(BaseModel):
    from_id: str
    to_id: str
    type: str
    props: dict[str, Any] = {}


class TextChunk(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any]


class ParsedBim(BaseModel):
    nodes: list[BimNode]
    relations: list[BimRelation]
    chunks: list[TextChunk]
    warnings: list[str] = []
