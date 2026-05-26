# P2.5 专家能力蓝图生成

你将根据 P2 产出的专家画像，生成用于后续访谈、隐性变量挖掘和技能生成的专家能力蓝图。

## 专家名称

{name}

## 用户补充描述

{user_description}

## P2 expert_profile.json

```json
{expert_profile_json}
```

## 补充材料摘要

{material_summary}

## 输出要求

只输出一个顶层 JSON 对象，顶层键必须是 `expert_blueprint`。不要输出 Markdown 解释、代码围栏或额外文本。

`expert_blueprint` 必须包含以下字段：

- `identity_summary`: object，概括专家姓名、角色、领域。
- `domain_summary`: string，概括该专家解决的问题域。
- `primary_workflows`: array，至少 2 项，每项描述一个核心工作流，并尽量包含 `evidence`。
- `decision_scenarios`: array，至少 3 项，每项描述一个能暴露判断能力的场景，并尽量包含 `evidence`。
- `knowledge_shape`: object，包含 `primary`、`secondary`、`reason`，说明知识形态。
- `reasoning_framework`: array，列出显性判断框架，每项包含 `name`、`description`，并尽量包含 `evidence`。
- `tacit_knowledge_targets`: array，至少 5 项，每项包含 `label`、`description`，并尽量包含 `evidence`。
- `type_match`: object，包含 `recommended_type`、`confidence`、`matched_signals`、`rejected_types`。
- `generation_strategy`: object，包含 `mode`（`preset` 或 `generic`）、`output_sections`、`heuristics_shape`。
- `scope_boundaries`: array，描述该专家技能不应覆盖的边界。
- `evidence`: array，列出使用到的 profile 路径或材料证据。

内置类型只是候选项。只有当材料强烈匹配某一内置类型时，才将 `generation_strategy.mode` 设为 `preset`；否则推荐 `custom` 或低置信度匹配，并让系统使用通用生成。

## 输出格式

```json
{
  "expert_blueprint": {
    "identity_summary": {
      "name": "{name}",
      "role": "",
      "domain": ""
    },
    "domain_summary": "",
    "primary_workflows": [
      {"name": "", "evidence": "profile.visible_knowledge[0]"},
      {"name": "", "evidence": "profile.known_decisions[0]"}
    ],
    "decision_scenarios": [
      {"scenario": "", "evidence": "profile.known_decisions[0]"},
      {"scenario": "", "evidence": "profile.known_decisions[1]"},
      {"scenario": "", "evidence": "profile.suspected_gaps[0]"}
    ],
    "knowledge_shape": {
      "primary": "",
      "secondary": [],
      "reason": ""
    },
    "reasoning_framework": [
      {"name": "", "description": "", "evidence": "profile.visible_knowledge[0]"}
    ],
    "tacit_knowledge_targets": [
      {"label": "", "description": "", "evidence": "profile.suspected_gaps[0]"},
      {"label": "", "description": "", "evidence": "profile.suspected_gaps[1]"},
      {"label": "", "description": "", "evidence": "profile.suspected_gaps[2]"},
      {"label": "", "description": "", "evidence": "profile.known_decisions[0]"},
      {"label": "", "description": "", "evidence": "profile.visible_knowledge[0]"}
    ],
    "type_match": {
      "recommended_type": "custom",
      "confidence": 0.0,
      "matched_signals": [],
      "rejected_types": [
        {"type": "", "reason": ""}
      ]
    },
    "generation_strategy": {
      "mode": "generic",
      "output_sections": [],
      "heuristics_shape": ""
    },
    "scope_boundaries": [
      {"boundary": "", "evidence": "profile.visible_knowledge[0]"}
    ],
    "evidence": []
  }
}
```
