#!/usr/bin/env python3
"""Generic/custom expert skill artifact rendering from expert blueprints."""

from __future__ import annotations

import json


def _item_text(item: object, *keys: str) -> str:
    if isinstance(item, dict):
        for key in keys:
            value = item.get(key)
            if value:
                return str(value)
        return json.dumps(item, ensure_ascii=False)
    return str(item)


def render_generic_expertise(base_content: str, blueprint: dict) -> str:
    """Render expertise.md content for blueprint-driven custom experts."""
    lines: list[str] = []
    if base_content.strip():
        lines.extend([base_content.rstrip(), ""])

    lines.extend(
        [
            "## 专家能力蓝图",
            "",
            "### 领域摘要",
            str(blueprint.get("domain_summary") or "（未提供）"),
            "",
            "### 核心工作流",
        ]
    )
    for item in blueprint.get("primary_workflows", []):
        lines.append(f"- {_item_text(item, 'name', 'workflow', 'description')}")

    lines.extend(["", "### 典型决策场景"])
    for item in blueprint.get("decision_scenarios", []):
        lines.append(f"- {_item_text(item, 'scenario', 'name', 'description')}")

    lines.extend(["", "### 判断框架"])
    for item in blueprint.get("reasoning_framework", []):
        if isinstance(item, dict):
            name = item.get("name", "")
            desc = item.get("description", "")
            lines.append(f"- {name}：{desc}" if desc else f"- {name}")
        else:
            lines.append(f"- {item}")

    lines.extend(["", "### 隐性知识目标"])
    for item in blueprint.get("tacit_knowledge_targets", []):
        if isinstance(item, dict):
            label = item.get("label", "")
            desc = item.get("description", "")
            lines.append(f"- {label}：{desc}" if desc else f"- {label}")
        else:
            lines.append(f"- {item}")

    lines.extend(["", "### 边界条件"])
    for item in blueprint.get("scope_boundaries", []):
        lines.append(f"- {_item_text(item, 'boundary', 'description')}")

    lines.append("")
    return "\n".join(lines)


def render_generic_heuristics(
    name: str,
    expertise_type: str,
    preset: dict,
    blueprint: dict,
) -> dict:
    """Render heuristics.json for blueprint-driven custom experts."""
    return {
        "expert": name,
        "expertise_type": expertise_type,
        "knowledge_format": preset["knowledge_format"],
        "execution_model": preset["execution_model"],
        "sections": preset["knowledge_sections"],
        "rules": [],
        "blueprint": {
            "knowledge_shape": blueprint.get("knowledge_shape", {}),
            "primary_workflows": blueprint.get("primary_workflows", []),
            "decision_scenarios": blueprint.get("decision_scenarios", []),
            "reasoning_framework": blueprint.get("reasoning_framework", []),
            "tacit_knowledge_targets": blueprint.get("tacit_knowledge_targets", []),
            "scope_boundaries": blueprint.get("scope_boundaries", []),
        },
    }


def render_generic_knowledge_graph(name: str, preset: dict, blueprint: dict) -> str:
    """Render knowledge_graph.md for blueprint-driven custom experts."""
    lines = [
        f"# {name} — 知识图谱",
        "",
        f"## 专长类型: {preset['display_name']}",
        "",
        "## 蓝图工作流",
        "",
        "| 工作流 |",
        "|--------|",
    ]
    for item in blueprint.get("primary_workflows", []):
        lines.append(f"| {_item_text(item, 'name', 'workflow', 'description')} |")

    lines.extend(["", "## 决策场景", "", "| 场景 |", "|------|"])
    for item in blueprint.get("decision_scenarios", []):
        lines.append(f"| {_item_text(item, 'scenario', 'name', 'description')} |")

    lines.extend(["", "## 隐性知识目标", "", "| 目标 | 描述 |", "|------|------|"])
    for item in blueprint.get("tacit_knowledge_targets", []):
        if isinstance(item, dict):
            lines.append(f"| {item.get('label', '')} | {item.get('description', '')} |")
        else:
            lines.append(f"| {item} | |")

    lines.append("")
    return "\n".join(lines)
