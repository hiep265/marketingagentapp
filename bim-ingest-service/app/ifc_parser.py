from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable

import ifcopenshell
import ifcopenshell.util.element

from .models import BimNode, BimRelation, ParsedBim, TextChunk


SPATIAL_TYPES = {"IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"}
ELEMENT_TYPES = {
    "IfcElement",
    "IfcDoor",
    "IfcWindow",
    "IfcWall",
    "IfcWallStandardCase",
    "IfcSlab",
    "IfcColumn",
    "IfcBeam",
    "IfcStair",
    "IfcRailing",
    "IfcRoof",
    "IfcCovering",
    "IfcFurnishingElement",
    "IfcFlowTerminal",
    "IfcFlowSegment",
    "IfcFlowController",
    "IfcFlowFitting",
    "IfcFlowMovingDevice",
    "IfcDistributionElement",
}


def resolve_ifc_path(path: str, workspace_prefix: str, workspace_mount: str) -> Path:
    raw = Path(path)
    if str(raw).startswith(workspace_prefix):
        raw = Path(workspace_mount) / str(raw).removeprefix(workspace_prefix).lstrip("/")
    return raw


def open_ifc(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"IFC file not found: {path}")

    if path.suffix.lower() != ".ifczip":
        return ifcopenshell.open(str(path)), None

    tmp = tempfile.TemporaryDirectory(prefix="ifczip-")
    with zipfile.ZipFile(path) as archive:
        candidates = [name for name in archive.namelist() if name.lower().endswith(".ifc")]
        if not candidates:
            tmp.cleanup()
            raise ValueError(f"No .ifc file found inside {path}")
        archive.extract(candidates[0], tmp.name)
        extracted = Path(tmp.name) / candidates[0]
    return ifcopenshell.open(str(extracted)), tmp


def safe_get(entity: Any, attr: str, default: Any = None) -> Any:
    try:
        value = getattr(entity, attr)
    except Exception:
        return default
    return default if value is None else value


def global_id(entity: Any) -> str:
    value = safe_get(entity, "GlobalId")
    return str(value) if value else f"{entity.is_a()}:{entity.id()}"


def node_id(project_id: str, entity: Any) -> str:
    return f"{project_id}:{global_id(entity)}"


def entity_name(entity: Any) -> str:
    return str(safe_get(entity, "Name", "") or safe_get(entity, "LongName", "") or global_id(entity))


def as_primitive(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [as_primitive(v) for v in value if as_primitive(v) is not None]
    if hasattr(value, "wrappedValue"):
        return as_primitive(value.wrappedValue)
    if hasattr(value, "is_a"):
        return {"type": value.is_a(), "id": getattr(value, "id", lambda: None)()}
    return str(value)


def compact_props(props: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in props.items():
        if value is None or value == "":
            continue
        primitive = as_primitive(value)
        if primitive is not None and primitive != "":
            clean[key] = primitive
    return clean


def psets_for(entity: Any) -> dict[str, Any]:
    try:
        psets = ifcopenshell.util.element.get_psets(entity)
    except Exception:
        return {}
    clean: dict[str, Any] = {}
    for set_name, values in psets.items():
        if not isinstance(values, dict):
            continue
        clean[set_name] = {k: as_primitive(v) for k, v in values.items() if k != "id" and as_primitive(v) is not None}
    return clean


def material_names(entity: Any) -> list[str]:
    names: list[str] = []
    try:
        material = ifcopenshell.util.element.get_material(entity, should_skip_usage=True)
    except Exception:
        return names
    if material is None:
        return names
    candidates: Iterable[Any]
    if hasattr(material, "MaterialLayers"):
        candidates = material.MaterialLayers
    elif hasattr(material, "Materials"):
        candidates = material.Materials
    else:
        candidates = [material]
    for item in candidates:
        mat = safe_get(item, "Material", item)
        name = safe_get(mat, "Name")
        if name:
            names.append(str(name))
    return sorted(set(names))


def container_for(entity: Any) -> Any | None:
    try:
        return ifcopenshell.util.element.get_container(entity)
    except Exception:
        return None


def type_for(entity: Any) -> Any | None:
    try:
        return ifcopenshell.util.element.get_type(entity)
    except Exception:
        return None


def decomposition_children(entity: Any) -> list[Any]:
    children: list[Any] = []
    for rel in safe_get(entity, "IsDecomposedBy", []) or []:
        if getattr(rel, "is_a", lambda *_: False)("IfcRelAggregates"):
            children.extend(list(safe_get(rel, "RelatedObjects", []) or []))
    return children


def base_props(project_id: str, entity: Any, label: str) -> dict[str, Any]:
    props = {
        "project_id": project_id,
        "global_id": global_id(entity),
        "ifc_class": entity.is_a(),
        "name": safe_get(entity, "Name"),
        "long_name": safe_get(entity, "LongName"),
        "description": safe_get(entity, "Description"),
        "object_type": safe_get(entity, "ObjectType"),
        "predefined_type": safe_get(entity, "PredefinedType"),
        "label": label,
    }
    if entity.is_a("IfcBuildingStorey"):
        props["elevation"] = safe_get(entity, "Elevation")
    return compact_props(props)


def add_entity_node(nodes: dict[str, BimNode], project_id: str, entity: Any, label: str) -> str:
    nid = node_id(project_id, entity)
    nodes[nid] = BimNode(id=nid, label=label, props=base_props(project_id, entity, label))
    return nid


def add_property_nodes(
    nodes: dict[str, BimNode],
    relations: list[BimRelation],
    chunks: list[TextChunk],
    project_id: str,
    entity: Any,
    owner_id: str,
) -> None:
    psets = psets_for(entity)
    flat_lines: list[str] = []
    for pset_name, values in psets.items():
        pset_id = f"{owner_id}:pset:{pset_name}"
        nodes[pset_id] = BimNode(
            id=pset_id,
            label="PropertySet",
            props={"project_id": project_id, "name": pset_name, "label": "PropertySet"},
        )
        relations.append(BimRelation(from_id=owner_id, to_id=pset_id, type="HAS_PROPERTY_SET"))
        for prop_name, prop_value in values.items():
            prop_id = f"{pset_id}:{prop_name}"
            nodes[prop_id] = BimNode(
                id=prop_id,
                label="Property",
                props={
                    "project_id": project_id,
                    "name": prop_name,
                    "value": prop_value if isinstance(prop_value, (str, int, float, bool)) else str(prop_value),
                    "label": "Property",
                },
            )
            relations.append(BimRelation(from_id=pset_id, to_id=prop_id, type="HAS_PROPERTY"))
            flat_lines.append(f"{pset_name}.{prop_name}: {prop_value}")

    if flat_lines:
        chunks.append(
            TextChunk(
                id=f"{owner_id}:properties",
                text=f"Properties for {entity.is_a()} {entity_name(entity)} ({global_id(entity)}):\n" + "\n".join(flat_lines),
                metadata={"project_id": project_id, "global_id": global_id(entity), "kind": "properties"},
            )
        )


def add_material_nodes(
    nodes: dict[str, BimNode],
    relations: list[BimRelation],
    project_id: str,
    owner_id: str,
    materials: list[str],
) -> None:
    for material in materials:
        material_id = f"{project_id}:material:{material}"
        nodes[material_id] = BimNode(
            id=material_id,
            label="Material",
            props={"project_id": project_id, "name": material, "label": "Material"},
        )
        relations.append(BimRelation(from_id=owner_id, to_id=material_id, type="HAS_MATERIAL"))


def element_text(entity: Any, container: Any | None, type_entity: Any | None, materials: list[str]) -> str:
    parts = [
        f"IFC element {entity_name(entity)}",
        f"GlobalId: {global_id(entity)}",
        f"Class: {entity.is_a()}",
    ]
    predefined = safe_get(entity, "PredefinedType")
    if predefined:
        parts.append(f"Predefined type: {predefined}")
    if type_entity is not None:
        parts.append(f"Type: {entity_name(type_entity)} ({type_entity.is_a()})")
    if container is not None:
        parts.append(f"Contained in: {entity_name(container)} ({container.is_a()})")
    if materials:
        parts.append("Materials: " + ", ".join(materials))
    description = safe_get(entity, "Description")
    if description:
        parts.append(f"Description: {description}")
    return "\n".join(parts)


def parse_ifc(path: Path, project_id: str) -> ParsedBim:
    model, tmp = open_ifc(path)
    nodes: dict[str, BimNode] = {}
    relations: list[BimRelation] = []
    chunks: list[TextChunk] = []
    warnings: list[str] = []

    try:
        projects = model.by_type("IfcProject")
        if not projects:
            warnings.append("No IfcProject found")
        for project in projects:
            project_node_id = add_entity_node(nodes, project_id, project, "Project")
            chunks.append(
                TextChunk(
                    id=f"{project_node_id}:summary",
                    text=f"BIM project {entity_name(project)}. GlobalId: {global_id(project)}. IFC schema: {model.schema}.",
                    metadata={"project_id": project_id, "global_id": global_id(project), "kind": "project"},
                )
            )

        label_by_ifc = {
            "IfcSite": "Site",
            "IfcBuilding": "Building",
            "IfcBuildingStorey": "Storey",
            "IfcSpace": "Space",
        }
        for ifc_type, label in label_by_ifc.items():
            for entity in model.by_type(ifc_type):
                entity_id = add_entity_node(nodes, project_id, entity, label)
                chunks.append(
                    TextChunk(
                        id=f"{entity_id}:summary",
                        text=f"{label} {entity_name(entity)}. GlobalId: {global_id(entity)}. IFC class: {entity.is_a()}.",
                        metadata={"project_id": project_id, "global_id": global_id(entity), "kind": label.lower()},
                    )
                )

        for entity in list(nodes.values()):
            pass

        for parent_type in ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey"]:
            for parent in model.by_type(parent_type):
                parent_id = node_id(project_id, parent)
                for child in decomposition_children(parent):
                    if not hasattr(child, "is_a") or child.is_a() not in SPATIAL_TYPES:
                        continue
                    if child.is_a("IfcSite"):
                        rel_type = "HAS_SITE"
                    elif child.is_a("IfcBuilding"):
                        rel_type = "HAS_BUILDING"
                    elif child.is_a("IfcBuildingStorey"):
                        rel_type = "HAS_STOREY"
                    elif child.is_a("IfcSpace"):
                        rel_type = "CONTAINS_SPACE"
                    else:
                        rel_type = "CONTAINS"
                    relations.append(BimRelation(from_id=parent_id, to_id=node_id(project_id, child), type=rel_type))

        seen_elements: set[str] = set()
        for ifc_type in ELEMENT_TYPES:
            try:
                candidates = model.by_type(ifc_type)
            except Exception:
                continue
            for entity in candidates:
                gid = global_id(entity)
                if gid in seen_elements or entity.is_a() in SPATIAL_TYPES:
                    continue
                seen_elements.add(gid)

                element_id = add_entity_node(nodes, project_id, entity, "Element")
                container = container_for(entity)
                type_entity = type_for(entity)
                materials = material_names(entity)
                add_material_nodes(nodes, relations, project_id, element_id, materials)
                add_property_nodes(nodes, relations, chunks, project_id, entity, element_id)

                if container is not None:
                    container_id = node_id(project_id, container)
                    if container_id in nodes:
                        rel_type = "CONTAINS_ELEMENT" if container.is_a("IfcSpace") else "CONTAINS"
                        relations.append(BimRelation(from_id=container_id, to_id=element_id, type=rel_type))

                if type_entity is not None:
                    type_id = node_id(project_id, type_entity)
                    if type_id not in nodes:
                        nodes[type_id] = BimNode(
                            id=type_id,
                            label="Type",
                            props=base_props(project_id, type_entity, "Type"),
                        )
                    relations.append(BimRelation(from_id=element_id, to_id=type_id, type="HAS_TYPE"))

                chunks.append(
                    TextChunk(
                        id=f"{element_id}:summary",
                        text=element_text(entity, container, type_entity, materials),
                        metadata={
                            "project_id": project_id,
                            "global_id": gid,
                            "ifc_class": entity.is_a(),
                            "kind": "element",
                        },
                    )
                )

        return ParsedBim(nodes=list(nodes.values()), relations=relations, chunks=chunks, warnings=warnings)
    finally:
        if tmp is not None:
            tmp.cleanup()
