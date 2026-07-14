from __future__ import annotations

import re
from typing import Any

from neo4j import GraphDatabase

from .models import BimNode, BimRelation, GraphQueryRequest, ParsedBim


ALLOWED_LABELS = {
    "Project",
    "Site",
    "Building",
    "Storey",
    "Space",
    "Element",
    "Type",
    "Material",
    "PropertySet",
    "Property",
    "System",
    "Classification",
}
ALLOWED_RELS = {
    "HAS_SITE",
    "HAS_BUILDING",
    "HAS_STOREY",
    "CONTAINS_SPACE",
    "CONTAINS_ELEMENT",
    "CONTAINS",
    "HAS_TYPE",
    "HAS_PROPERTY_SET",
    "HAS_PROPERTY",
    "HAS_MATERIAL",
    "HAS_SYSTEM",
    "HAS_CLASSIFICATION",
}


def safe_label(label: str) -> str:
    if label not in ALLOWED_LABELS:
        return "Element"
    return label


def safe_rel(rel_type: str) -> str:
    if rel_type not in ALLOWED_RELS:
        return "CONTAINS"
    return rel_type


def compact_record(record: Any) -> dict[str, Any]:
    return {key: record[key] for key in record.keys()}


class BimGraph:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def ensure_schema(self) -> None:
        statements = [
            "CREATE CONSTRAINT bim_entity_id IF NOT EXISTS FOR (n:BimEntity) REQUIRE n.id IS UNIQUE",
            "CREATE INDEX bim_entity_project IF NOT EXISTS FOR (n:BimEntity) ON (n.project_id)",
            "CREATE INDEX bim_entity_global_id IF NOT EXISTS FOR (n:BimEntity) ON (n.global_id)",
            "CREATE INDEX bim_entity_ifc_class IF NOT EXISTS FOR (n:BimEntity) ON (n.ifc_class)",
            "CREATE INDEX bim_entity_name IF NOT EXISTS FOR (n:BimEntity) ON (n.name)",
        ]
        with self.driver.session() as session:
            for statement in statements:
                session.run(statement)

    def clear_project(self, project_id: str) -> None:
        with self.driver.session() as session:
            session.run("MATCH (n:BimEntity {project_id: $project_id}) DETACH DELETE n", project_id=project_id)

    def upsert_node(self, node: BimNode) -> None:
        label = safe_label(node.label)
        props = dict(node.props)
        props["id"] = node.id
        with self.driver.session() as session:
            session.run(
                f"MERGE (n:BimEntity:{label} {{id: $id}}) SET n += $props",
                id=node.id,
                props=props,
            )

    def upsert_relation(self, relation: BimRelation, project_id: str) -> None:
        rel_type = safe_rel(relation.type)
        props = dict(relation.props)
        props["project_id"] = project_id
        with self.driver.session() as session:
            session.run(
                f"""
                MATCH (a:BimEntity {{id: $from_id}})
                MATCH (b:BimEntity {{id: $to_id}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $props
                """,
                from_id=relation.from_id,
                to_id=relation.to_id,
                props=props,
            )

    def ingest(self, project_id: str, parsed: ParsedBim, replace: bool) -> dict[str, int]:
        self.ensure_schema()
        if replace:
            self.clear_project(project_id)
        for node in parsed.nodes:
            self.upsert_node(node)
        for relation in parsed.relations:
            self.upsert_relation(relation, project_id)
        return {"nodes": len(parsed.nodes), "relations": len(parsed.relations), "chunks": len(parsed.chunks)}

    def get_element(self, project_id: str, global_id: str) -> dict[str, Any] | None:
        with self.driver.session() as session:
            record = session.run(
                """
                MATCH (e:BimEntity {project_id: $project_id, global_id: $global_id})
                OPTIONAL MATCH (e)-[:HAS_PROPERTY_SET]->(ps:PropertySet)-[:HAS_PROPERTY]->(p:Property)
                OPTIONAL MATCH (e)-[:HAS_MATERIAL]->(m:Material)
                RETURN e{.*} AS element,
                       collect(DISTINCT ps.name + "." + p.name + "=" + toString(p.value)) AS properties,
                       collect(DISTINCT m.name) AS materials
                """,
                project_id=project_id,
                global_id=global_id,
            ).single()
        return compact_record(record) if record else None

    def list_spaces(self, project_id: str, storey: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        query = """
        MATCH (s:Space {project_id: $project_id})
        OPTIONAL MATCH (st:Storey {project_id: $project_id})-[:CONTAINS_SPACE]->(s)
        WITH s, st
        WHERE $storey IS NULL OR toLower(coalesce(st.name, '')) CONTAINS toLower($storey)
        RETURN s{.*} AS space, st{.*} AS storey
        ORDER BY st IS NULL, coalesce(st.name, ''), coalesce(s.name, '')
        LIMIT $limit
        """
        with self.driver.session() as session:
            return [compact_record(r) for r in session.run(query, project_id=project_id, storey=storey, limit=limit)]

    def node_types(self, project_id: str) -> dict[str, Any]:
        with self.driver.session() as session:
            labels = [
                compact_record(r)
                for r in session.run(
                    """
                    MATCH (n:BimEntity {project_id: $project_id})
                    RETURN n.label AS label, count(n) AS count
                    ORDER BY count DESC, label
                    """,
                    project_id=project_id,
                )
            ]
            classes = [
                compact_record(r)
                for r in session.run(
                    """
                    MATCH (n:BimEntity {project_id: $project_id})
                    WHERE n.ifc_class IS NOT NULL
                    RETURN n.ifc_class AS ifc_class, n.label AS label, count(n) AS count
                    ORDER BY count DESC, ifc_class, label
                    LIMIT 200
                    """,
                    project_id=project_id,
                )
            ]
            relations = [
                compact_record(r)
                for r in session.run(
                    """
                    MATCH (:BimEntity {project_id: $project_id})-[rel]->(:BimEntity {project_id: $project_id})
                    RETURN type(rel) AS type, count(rel) AS count
                    ORDER BY count DESC, type
                    """,
                    project_id=project_id,
                )
            ]
        return {"labels": labels, "ifc_classes": classes, "relations": relations}

    def count_entities(
        self,
        project_id: str,
        label: str | None,
        class_name: str | None,
        name: str | None,
        storey: str | None,
        space: str | None,
    ) -> dict[str, Any]:
        query = """
        MATCH (n:BimEntity {project_id: $project_id})
        WHERE ($label IS NULL OR n.label = $label OR toLower(coalesce(n.label, '')) = toLower($label))
          AND ($class_name IS NULL OR n.ifc_class = $class_name OR n.ifc_class STARTS WITH $class_name)
          AND ($name IS NULL OR toLower(coalesce(n.name, '')) CONTAINS toLower($name))
          AND (
            $storey IS NULL
            OR (n.label = 'Storey' AND toLower(coalesce(n.name, '')) CONTAINS toLower($storey))
            OR EXISTS {
              MATCH (st:Storey {project_id: $project_id})-[:CONTAINS|CONTAINS_SPACE|CONTAINS_ELEMENT*1..2]->(n)
              WHERE toLower(coalesce(st.name, '')) CONTAINS toLower($storey)
            }
          )
          AND (
            $space IS NULL
            OR (n.label = 'Space' AND toLower(coalesce(n.name, '')) CONTAINS toLower($space))
            OR EXISTS {
              MATCH (sp:Space {project_id: $project_id})-[:CONTAINS_ELEMENT]->(n)
              WHERE toLower(coalesce(sp.name, '')) CONTAINS toLower($space)
            }
          )
        RETURN count(DISTINCT n) AS count,
               collect(DISTINCT coalesce(n.global_id, n.id))[0..20] AS sample_ids
        """
        with self.driver.session() as session:
            record = session.run(
                query,
                project_id=project_id,
                label=label,
                class_name=class_name,
                name=name,
                storey=storey,
                space=space,
            ).single()
        return compact_record(record) if record else {"count": 0, "sample_ids": []}

    def list_entities(
        self,
        project_id: str,
        label: str | None,
        class_name: str | None,
        name: str | None,
        storey: str | None,
        space: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        query = """
        MATCH (n:BimEntity {project_id: $project_id})
        WHERE ($label IS NULL OR n.label = $label OR toLower(coalesce(n.label, '')) = toLower($label))
          AND ($class_name IS NULL OR n.ifc_class = $class_name OR n.ifc_class STARTS WITH $class_name)
          AND ($name IS NULL OR toLower(coalesce(n.name, '')) CONTAINS toLower($name))
          AND (
            $storey IS NULL
            OR (n.label = 'Storey' AND toLower(coalesce(n.name, '')) CONTAINS toLower($storey))
            OR EXISTS {
              MATCH (st:Storey {project_id: $project_id})-[:CONTAINS|CONTAINS_SPACE|CONTAINS_ELEMENT*1..2]->(n)
              WHERE toLower(coalesce(st.name, '')) CONTAINS toLower($storey)
            }
          )
          AND (
            $space IS NULL
            OR (n.label = 'Space' AND toLower(coalesce(n.name, '')) CONTAINS toLower($space))
            OR EXISTS {
              MATCH (sp:Space {project_id: $project_id})-[:CONTAINS_ELEMENT]->(n)
              WHERE toLower(coalesce(sp.name, '')) CONTAINS toLower($space)
            }
          )
        OPTIONAL MATCH (st:Storey {project_id: $project_id})-[:CONTAINS|CONTAINS_SPACE|CONTAINS_ELEMENT*1..2]->(n)
        WITH n, collect(DISTINCT st{.*})[0] AS storey
        OPTIONAL MATCH (sp:Space {project_id: $project_id})-[:CONTAINS_ELEMENT]->(n)
        RETURN n{.*} AS entity, storey, collect(DISTINCT sp{.*})[0] AS space
        ORDER BY coalesce(entity.label, ''), coalesce(storey.name, ''), coalesce(space.name, ''), coalesce(entity.name, ''), coalesce(entity.global_id, '')
        LIMIT $limit
        """
        with self.driver.session() as session:
            return [
                compact_record(r)
                for r in session.run(
                    query,
                    project_id=project_id,
                    label=label,
                    class_name=class_name,
                    name=name,
                    storey=storey,
                    space=space,
                    limit=limit,
                )
            ]

    def count_elements(self, project_id: str, class_name: str | None, storey: str | None, space: str | None) -> dict[str, Any]:
        query = """
        MATCH (e:Element {project_id: $project_id})
        OPTIONAL MATCH (space:Space)-[:CONTAINS_ELEMENT]->(e)
        OPTIONAL MATCH (storey:Storey)-[:CONTAINS|CONTAINS_SPACE|CONTAINS_ELEMENT*1..2]->(e)
        WITH e, space, storey
        WHERE ($class_name IS NULL OR e.ifc_class = $class_name OR e.ifc_class STARTS WITH $class_name)
          AND ($space IS NULL OR toLower(coalesce(space.name, '')) CONTAINS toLower($space))
          AND ($storey IS NULL OR toLower(coalesce(storey.name, '')) CONTAINS toLower($storey))
        RETURN count(DISTINCT e) AS count, collect(DISTINCT e.global_id)[0..20] AS sample_global_ids
        """
        with self.driver.session() as session:
            record = session.run(
                query,
                project_id=project_id,
                class_name=class_name,
                storey=storey,
                space=space,
            ).single()
        return compact_record(record) if record else {"count": 0, "sample_global_ids": []}

    def list_elements(self, project_id: str, class_name: str | None, storey: str | None, space: str | None, limit: int) -> list[dict[str, Any]]:
        query = """
        MATCH (e:Element {project_id: $project_id})
        OPTIONAL MATCH (space:Space)-[:CONTAINS_ELEMENT]->(e)
        OPTIONAL MATCH (storey:Storey)-[:CONTAINS|CONTAINS_SPACE|CONTAINS_ELEMENT*1..2]->(e)
        WITH e, space, storey
        WHERE ($class_name IS NULL OR e.ifc_class = $class_name OR e.ifc_class STARTS WITH $class_name)
          AND ($space IS NULL OR toLower(coalesce(space.name, '')) CONTAINS toLower($space))
          AND ($storey IS NULL OR toLower(coalesce(storey.name, '')) CONTAINS toLower($storey))
        RETURN e{.*} AS element, space{.*} AS space, storey{.*} AS storey
        ORDER BY coalesce(storey.name, ''), coalesce(space.name, ''), coalesce(e.name, '')
        LIMIT $limit
        """
        with self.driver.session() as session:
            return [
                compact_record(r)
                for r in session.run(
                    query,
                    project_id=project_id,
                    class_name=class_name,
                    storey=storey,
                    space=space,
                    limit=limit,
                )
            ]

    def property_search(
        self,
        project_id: str,
        property_name: str | None,
        property_value: str | None,
        class_name: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        query = """
        MATCH (e:Element {project_id: $project_id})-[:HAS_PROPERTY_SET]->(ps:PropertySet)-[:HAS_PROPERTY]->(p:Property)
        WHERE ($class_name IS NULL OR e.ifc_class = $class_name OR e.ifc_class STARTS WITH $class_name)
          AND ($property_name IS NULL OR toLower(p.name) CONTAINS toLower($property_name))
          AND ($property_value IS NULL OR toLower(toString(p.value)) CONTAINS toLower($property_value))
        RETURN e{.*} AS element, ps.name AS property_set, p.name AS property_name, p.value AS property_value
        ORDER BY coalesce(e.name, '')
        LIMIT $limit
        """
        with self.driver.session() as session:
            return [
                compact_record(r)
                for r in session.run(
                    query,
                    project_id=project_id,
                    property_name=property_name,
                    property_value=property_value,
                    class_name=class_name,
                    limit=limit,
                )
            ]

    def project_summary(self, project_id: str) -> dict[str, Any]:
        with self.driver.session() as session:
            labels = [
                compact_record(r)
                for r in session.run(
                    """
                    MATCH (n:BimEntity {project_id: $project_id})
                    RETURN n.label AS label, count(n) AS count
                    ORDER BY label
                    """,
                    project_id=project_id,
                )
            ]
            classes = [
                compact_record(r)
                for r in session.run(
                    """
                    MATCH (e:Element {project_id: $project_id})
                    RETURN e.ifc_class AS ifc_class, count(e) AS count
                    ORDER BY count DESC, ifc_class
                    """,
                    project_id=project_id,
                )
            ]
            spaces = [
                compact_record(r)
                for r in session.run(
                    """
                    MATCH (s:Space {project_id: $project_id})
                    OPTIONAL MATCH (st:Storey)-[:CONTAINS_SPACE]->(s)
                    RETURN s.name AS space, st.name AS storey
                    ORDER BY storey, space
                    LIMIT 20
                    """,
                    project_id=project_id,
                )
            ]
            properties = [
                compact_record(r)
                for r in session.run(
                    """
                    MATCH (:Element {project_id: $project_id})-[:HAS_PROPERTY_SET]->(ps:PropertySet)-[:HAS_PROPERTY]->(p:Property)
                    RETURN ps.name AS property_set, p.name AS property_name, count(p) AS count
                    ORDER BY count DESC, property_set, property_name
                    LIMIT 20
                    """,
                    project_id=project_id,
                )
            ]
        return {"labels": labels, "element_classes": classes, "spaces": spaces, "properties": properties}

    def run_intent(self, project_id: str, request: GraphQueryRequest) -> dict[str, Any]:
        if request.intent == "node_types":
            return {"result": self.node_types(project_id)}
        if request.intent == "count_entities":
            return {
                "result": self.count_entities(
                    project_id,
                    request.label,
                    request.class_name,
                    request.name,
                    request.storey,
                    request.space,
                )
            }
        if request.intent == "list_entities":
            return {
                "result": self.list_entities(
                    project_id,
                    request.label,
                    request.class_name,
                    request.name,
                    request.storey,
                    request.space,
                    request.limit,
                )
            }
        if request.intent == "count_elements":
            return {"result": self.count_elements(project_id, request.class_name, request.storey, request.space)}
        if request.intent == "list_elements":
            return {
                "result": self.list_elements(project_id, request.class_name, request.storey, request.space, request.limit)
            }
        if request.intent == "list_spaces":
            return {"result": self.list_spaces(project_id, request.storey, request.limit)}
        if request.intent == "get_element":
            if not request.global_id:
                raise ValueError("global_id is required for get_element")
            return {"result": self.get_element(project_id, request.global_id)}
        if request.intent == "property_search":
            return {
                "result": self.property_search(
                    project_id,
                    request.property_name,
                    request.property_value,
                    request.class_name,
                    request.limit,
                )
            }
        raise ValueError(f"Unsupported intent: {request.intent}")


def extract_storey(text: str) -> str | None:
    match = re.search(r"\b(?:tầng|storey|floor)\s*[:#-]?\s*([0-9]+[A-Za-z]?)\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip(" ?.,")
    match = re.search(r"\b(?:storey|floor)\s*[:#-]\s*([A-Za-z0-9_. -]+)", text, flags=re.IGNORECASE)
    return match.group(1).strip(" ?.,") if match else None


def label_from_question(text: str) -> str | None:
    lower = text.lower()
    pairs = [
        (["storey", "floor", "tầng", "tang"], "Storey"),
        (["space", "room", "phòng", "phong"], "Space"),
        (["project", "dự án", "du an"], "Project"),
        (["site", "khu đất", "khu dat"], "Site"),
        (["building", "tòa nhà", "toa nha", "nhà", "nha"], "Building"),
        (["material", "vật liệu", "vat lieu"], "Material"),
        (["property set", "pset", "bộ thuộc tính", "bo thuoc tinh"], "PropertySet"),
        (["property", "thuộc tính", "thuoc tinh"], "Property"),
        (["system", "hệ thống", "he thong"], "System"),
        (["classification", "phân loại", "phan loai"], "Classification"),
        (["type", "kiểu", "kieu"], "Type"),
    ]
    for keywords, label in pairs:
        if any(keyword in lower for keyword in keywords):
            return label
    explicit = re.search(r"\b(Project|Site|Building|Storey|Space|Element|Type|Material|PropertySet|Property|System|Classification)\b", text)
    return explicit.group(0) if explicit else None


def class_from_question(text: str) -> str | None:
    lower = text.lower()
    pairs = [
        (["cửa sổ", "window", "windows"], "IfcWindow"),
        (["cửa", "door", "doors"], "IfcDoor"),
        (["tường", "wall", "walls"], "IfcWall"),
        (["sàn", "slab", "floor slab"], "IfcSlab"),
        (["cột", "column", "columns"], "IfcColumn"),
        (["dầm", "beam", "beams"], "IfcBeam"),
        (["cầu thang", "stair", "stairs"], "IfcStair"),
        (["thiết bị", "equipment"], "IfcDistributionElement"),
    ]
    for keywords, ifc_class in pairs:
        if any(keyword in lower for keyword in keywords):
            return ifc_class
    explicit = re.search(r"\bIfc[A-Za-z0-9_]+\b", text)
    return explicit.group(0) if explicit else None
