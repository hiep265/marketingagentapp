from __future__ import annotations

from typing import Any

from .graph import BimGraph, class_from_question, extract_storey, label_from_question
from .lightrag import LightRagClient


COUNT_WORDS = ["bao nhiêu", "count", "how many", "số lượng", "so luong"]
LIST_WORDS = ["liệt kê", "list", "danh sách", "những", "các"]
PROPERTY_HINTS = ["chống cháy", "fire", "rating", "u-value", "thermal", "property", "thuộc tính"]


def is_count_question(question: str) -> bool:
    lower = question.lower()
    return any(word in lower for word in COUNT_WORDS)


def is_list_question(question: str) -> bool:
    lower = question.lower()
    return any(word in lower for word in LIST_WORDS)


def property_terms(question: str) -> tuple[str | None, str | None]:
    lower = question.lower()
    if "chống cháy" in lower or "fire" in lower:
        return "Fire", None
    if "2h" in lower or "2 giờ" in lower or "120" in lower:
        return "Fire", "120"
    return None, None


def answer_count(
    question: str,
    facts: dict[str, Any],
    class_name: str | None,
    label: str | None,
    storey: str | None,
) -> str:
    count = facts.get("count", 0)
    scope = f" ở tầng {storey}" if storey else ""
    subject = class_name or label or "BIM entity"
    samples = facts.get("sample_ids") or facts.get("sample_global_ids") or []
    return f"Tìm trong graph BIM: có {count} {subject}{scope}. Sample id: {samples}."


def answer_list(rows: list[dict[str, Any]], class_name: str | None, label: str | None = None) -> str:
    subject = class_name or label or "BIM entity"
    if not rows:
        return f"Không tìm thấy {subject} phù hợp trong graph BIM."
    names = []
    for row in rows[:20]:
        entity = row.get("entity") or row.get("element") or row.get("space") or {}
        names.append(
            f"{entity.get('name') or entity.get('global_id') or entity.get('id')} "
            f"({entity.get('ifc_class') or entity.get('label', '')})"
        )
    return f"Tìm thấy {len(rows)} {subject}. Một số kết quả: " + "; ".join(names)


def answer_summary(summary: dict[str, Any]) -> str:
    class_counts = ", ".join(
        f"{row.get('ifc_class')}: {row.get('count')}" for row in summary.get("element_classes", [])[:10]
    )
    spaces = ", ".join(
        f"{row.get('space')} ({row.get('storey')})" for row in summary.get("spaces", [])[:10]
    )
    properties = ", ".join(
        f"{row.get('property_set')}.{row.get('property_name')}" for row in summary.get("properties", [])[:10]
    )
    parts = ["Tóm tắt từ Neo4j BIM graph:"]
    if class_counts:
        parts.append(f"Element classes: {class_counts}.")
    if spaces:
        parts.append(f"Spaces: {spaces}.")
    if properties:
        parts.append(f"Properties nổi bật: {properties}.")
    return " ".join(parts)


async def ask_bim(graph: BimGraph, lightrag: LightRagClient, project_id: str, question: str, top_k: int) -> dict[str, Any]:
    class_name = class_from_question(question)
    label = None if class_name else label_from_question(question)
    storey = extract_storey(question)

    if is_count_question(question):
        facts = graph.count_entities(project_id, label, class_name, None, storey, None)
        return {
            "route": "neo4j",
            "answer": answer_count(question, facts, class_name, label, storey),
            "facts": facts,
        }

    prop_name, prop_value = property_terms(question)
    if prop_name or any(term in question.lower() for term in PROPERTY_HINTS):
        rows = graph.property_search(project_id, prop_name, prop_value, class_name, min(top_k * 5, 100))
        return {
            "route": "neo4j",
            "answer": answer_list(rows, class_name),
            "facts": rows,
        }

    if is_list_question(question):
        rows = graph.list_entities(project_id, label, class_name, None, storey, None, min(top_k * 5, 100))
        return {
            "route": "neo4j",
            "answer": answer_list(rows, class_name, label),
            "facts": rows,
        }

    rag = await lightrag.query(project_id, question, top_k)
    context_items = rag.get("contextItems") or rag.get("contexts") or rag.get("data") or []
    answer = rag.get("answer") or rag.get("response")
    if not answer:
        if context_items:
            answer = "Tôi tìm được ngữ cảnh liên quan trong LightRAG. Hãy dùng các đoạn context kèm theo để tổng hợp câu trả lời."
        else:
            summary = graph.project_summary(project_id)
            return {
                "route": "neo4j_summary",
                "answer": answer_summary(summary),
                "facts": summary,
                "lightrag": rag,
            }
    return {
        "route": "lightrag",
        "answer": answer,
        "facts": {"class_name": class_name, "label": label, "storey": storey},
        "lightrag": rag,
    }
