# Blueprint-First Expert Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the project create expert skills for unknown expert domains by inserting an expert blueprint stage and falling back to a generic/custom generator when no built-in type is a strong match.

**Architecture:** Add a P2.5 blueprint artifact after `expert_profile.json`, then let P3/P4 consume blueprint seeds and P7 render either preset-based or generic/custom artifacts. Keep the current prompt-file plus parse-output workflow; do not add model API calls or migrate existing skills.

**Tech Stack:** Python 3.10+, standard library JSON/YAML parsing pattern already used in `tools/*.py`, pytest-compatible test files under `tools/test_*.py`, Markdown prompts and docs.

---

## File Structure

- Create `prompts/discovery/expert_blueprint.md`: prompt for producing `expert_blueprint.json`.
- Create `tools/blueprint_builder.py`: P2.5 CLI for prompt assembly, parse-output validation, type resolution, and meta update.
- Create `tools/test_blueprint_builder.py`: tests for P2.5 behavior.
- Create `tools/generic_skill_renderer.py`: helper functions for generic/custom `expertise.md`, `heuristics.json`, and `knowledge_graph.md`.
- Create `mock_expert_unknown/discovery/*`: fixture for an unknown-domain custom expert smoke test.
- Modify `tools/discovery_schema.py`: add `blueprint_ready`, blueprint builder/validator helpers, and type-match resolution helper.
- Modify `tools/test_discovery_schema.py`: tests for blueprint schema and quality gates.
- Modify `tools/expertise_presets.py`: add first-class `custom` preset.
- Modify `tools/test_skill_writer.py`: tests for custom preset and blueprint-driven P7 output.
- Modify `tools/latent_variable_builder.py`: optionally read blueprint and include it in P3 prompt.
- Modify `tools/test_latent_variable_builder.py`: tests that P3 prompt embeds blueprint seeds while old behavior works.
- Modify `tools/triplet_generator.py`: optionally read blueprint and include decision scenarios in P4 prompt.
- Modify `tools/test_triplet_generator.py`: tests that P4 prompt embeds blueprint scenarios while old behavior works.
- Modify `tools/skill_writer.py`: accept `blueprint` input and use generic renderer when `custom` or `generation_strategy.mode == "generic"`.
- Modify `tools/test_e2e_mock.py`: add custom unknown-domain smoke coverage without breaking current mock P2-P7 tests.
- Modify `README.md` and `SKILL.md`: document that type is inferred and `custom` is the generic fallback.

## Task 1: Blueprint Schema Helpers

**Files:**
- Modify: `tools/discovery_schema.py`
- Modify: `tools/test_discovery_schema.py`

- [ ] **Step 1: Write failing tests for blueprint status, validation, and type resolution**

Add this helper and tests near the existing discovery schema fixtures in `tools/test_discovery_schema.py`:

```python
def _make_blueprint(
    recommended_type="reviewer",
    confidence=0.91,
    mode="preset",
    workflows=None,
    scenarios=None,
    tacit_targets=None,
    output_sections=None,
):
    return {
        "identity_summary": {"name": "王五", "role": "投委会专家", "domain": "投资决策"},
        "domain_summary": "投资委员会项目评估与风险取舍。",
        "primary_workflows": workflows or [
            {"name": "项目初筛", "evidence": "profile.visible_knowledge[0]"},
            {"name": "投委会表决", "evidence": "profile.known_decisions[0]"},
        ],
        "decision_scenarios": scenarios or [
            {"scenario": "增长和现金流冲突时是否继续推进", "evidence": "profile.known_decisions[0]"},
            {"scenario": "创始团队经验不足但市场窗口明确", "evidence": "profile.known_decisions[1]"},
            {"scenario": "估值偏高但战略协同强", "evidence": "profile.suspected_gaps[0]"},
        ],
        "knowledge_shape": {
            "primary": "decision",
            "secondary": ["review"],
            "reason": "材料显示专家主要做风险取舍和项目评估。",
        },
        "reasoning_framework": [
            {"name": "风险收益权衡", "description": "比较下行风险与战略收益", "evidence": "profile.visible_knowledge[0]"}
        ],
        "tacit_knowledge_targets": tacit_targets or [
            {"label": "窗口期", "description": "何时接受估值溢价", "evidence": "profile.known_decisions[0]"},
            {"label": "团队可信度", "description": "创始团队缺口如何影响决策", "evidence": "profile.known_decisions[1]"},
            {"label": "退出确定性", "description": "退出路径是否压倒短期增长", "evidence": "profile.suspected_gaps[0]"},
            {"label": "协同强度", "description": "战略协同对财务指标的补偿", "evidence": "profile.visible_knowledge[1]"},
            {"label": "风险可控性", "description": "风险是否可被条款控制", "evidence": "profile.visible_knowledge[2]"},
        ],
        "type_match": {
            "recommended_type": recommended_type,
            "confidence": confidence,
            "matched_signals": ["评估", "风险", "决策"],
            "rejected_types": [{"type": "operator", "reason": "不是操作 SOP"}],
        },
        "generation_strategy": {
            "mode": mode,
            "output_sections": output_sections or ["适用场景", "判断框架", "隐性变量", "边界条件"],
            "heuristics_shape": "decision_framework",
        },
        "scope_boundaries": [
            {"boundary": "不替代法律或财务尽调", "evidence": "profile.visible_knowledge[3]"}
        ],
        "evidence": ["profile.visible_knowledge[0]", "profile.known_decisions[0]"],
    }


class TestExpertBlueprintSchema(unittest.TestCase):
    def test_blueprint_ready_is_valid_status(self):
        self.assertIn("blueprint_ready", DISCOVERY_STATUSES)

    def test_valid_expert_blueprint_passes(self):
        errors = validate_expert_blueprint(_make_blueprint())
        self.assertEqual(errors, [])

    def test_blueprint_requires_two_workflows(self):
        errors = validate_expert_blueprint(_make_blueprint(workflows=[{"name": "项目初筛"}]))
        self.assertTrue(any("primary_workflows" in e for e in errors))

    def test_blueprint_requires_three_decision_scenarios(self):
        errors = validate_expert_blueprint(_make_blueprint(scenarios=[{"scenario": "仅一个场景"}]))
        self.assertTrue(any("decision_scenarios" in e for e in errors))

    def test_blueprint_requires_five_tacit_targets(self):
        errors = validate_expert_blueprint(_make_blueprint(tacit_targets=[{"label": "窗口期"}]))
        self.assertTrue(any("tacit_knowledge_targets" in e for e in errors))

    def test_blueprint_requires_output_sections(self):
        errors = validate_expert_blueprint(_make_blueprint(output_sections=[]))
        self.assertTrue(any("generation_strategy.output_sections" in e for e in errors))

    def test_high_confidence_existing_type_uses_preset(self):
        resolved = resolve_blueprint_type_match(_make_blueprint("reviewer", 0.9), ["reviewer", "custom"])
        self.assertEqual(resolved["effective_type"], "reviewer")
        self.assertEqual(resolved["generation_mode"], "preset")
        self.assertFalse(resolved["type_match_overridden"])

    def test_low_confidence_downgrades_to_custom(self):
        resolved = resolve_blueprint_type_match(_make_blueprint("reviewer", 0.62), ["reviewer", "custom"])
        self.assertEqual(resolved["effective_type"], "custom")
        self.assertEqual(resolved["generation_mode"], "generic")
        self.assertTrue(resolved["type_match_overridden"])

    def test_missing_preset_downgrades_to_custom(self):
        resolved = resolve_blueprint_type_match(_make_blueprint("negotiation", 0.91), ["reviewer", "custom"])
        self.assertEqual(resolved["effective_type"], "custom")
        self.assertEqual(resolved["generation_mode"], "generic")
        self.assertTrue(resolved["type_match_overridden"])
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_discovery_schema.py
```

Expected: FAIL with import/name errors for `validate_expert_blueprint` and `resolve_blueprint_type_match`, and status assertion failing for `blueprint_ready`.

- [ ] **Step 3: Implement blueprint schema helpers**

In `tools/discovery_schema.py`, add `blueprint_ready` after `profile_ready` in `DISCOVERY_STATUSES`, then add these functions after `build_triplet_analysis`:

```python
def build_expert_blueprint(
    identity_summary: dict,
    domain_summary: str,
    primary_workflows: list[dict],
    decision_scenarios: list[dict],
    knowledge_shape: dict,
    reasoning_framework: list[dict],
    tacit_knowledge_targets: list[dict],
    type_match: dict,
    generation_strategy: dict,
    scope_boundaries: list[dict] | None = None,
    evidence: list[str] | None = None,
) -> dict:
    """Build an expert capability blueprint for blueprint-first creation."""
    return {
        "identity_summary": identity_summary,
        "domain_summary": domain_summary,
        "primary_workflows": primary_workflows,
        "decision_scenarios": decision_scenarios,
        "knowledge_shape": knowledge_shape,
        "reasoning_framework": reasoning_framework,
        "tacit_knowledge_targets": tacit_knowledge_targets,
        "type_match": type_match,
        "generation_strategy": generation_strategy,
        "scope_boundaries": scope_boundaries or [],
        "evidence": evidence or [],
    }


def validate_expert_blueprint(blueprint: dict) -> list[str]:
    """Validate an expert blueprint dict. Returns a list of errors."""
    errors: list[str] = []
    for field in (
        "identity_summary",
        "domain_summary",
        "primary_workflows",
        "decision_scenarios",
        "knowledge_shape",
        "reasoning_framework",
        "tacit_knowledge_targets",
        "type_match",
        "generation_strategy",
        "scope_boundaries",
        "evidence",
    ):
        if field not in blueprint:
            errors.append(f"{field} is required")

    if not isinstance(blueprint.get("identity_summary", {}), dict):
        errors.append("identity_summary must be a dict")
    if not blueprint.get("domain_summary"):
        errors.append("domain_summary is required")

    workflows = blueprint.get("primary_workflows", [])
    if not isinstance(workflows, list):
        errors.append("primary_workflows must be a list")
    elif len(workflows) < 2:
        errors.append(f"primary_workflows must contain at least 2 items, got {len(workflows)}")

    scenarios = blueprint.get("decision_scenarios", [])
    if not isinstance(scenarios, list):
        errors.append("decision_scenarios must be a list")
    elif len(scenarios) < 3:
        errors.append(f"decision_scenarios must contain at least 3 items, got {len(scenarios)}")

    targets = blueprint.get("tacit_knowledge_targets", [])
    if not isinstance(targets, list):
        errors.append("tacit_knowledge_targets must be a list")
    elif len(targets) < 5:
        errors.append(f"tacit_knowledge_targets must contain at least 5 items, got {len(targets)}")

    knowledge_shape = blueprint.get("knowledge_shape", {})
    if not isinstance(knowledge_shape, dict):
        errors.append("knowledge_shape must be a dict")
    elif not knowledge_shape.get("primary"):
        errors.append("knowledge_shape.primary is required")

    type_match = blueprint.get("type_match", {})
    if not isinstance(type_match, dict):
        errors.append("type_match must be a dict")
    else:
        if not type_match.get("recommended_type"):
            errors.append("type_match.recommended_type is required")
        confidence = type_match.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            errors.append("type_match.confidence must be a number")
        elif not (0 <= confidence <= 1):
            errors.append("type_match.confidence must be between 0 and 1")

    strategy = blueprint.get("generation_strategy", {})
    if not isinstance(strategy, dict):
        errors.append("generation_strategy must be a dict")
    else:
        if strategy.get("mode") not in ("preset", "generic"):
            errors.append("generation_strategy.mode must be 'preset' or 'generic'")
        sections = strategy.get("output_sections", [])
        if not isinstance(sections, list) or not sections:
            errors.append("generation_strategy.output_sections must be a non-empty list")
        if not strategy.get("heuristics_shape"):
            errors.append("generation_strategy.heuristics_shape is required")

    evidence = blueprint.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence must be a non-empty list")
    return errors


def resolve_blueprint_type_match(
    blueprint: dict,
    available_types: list[str],
    confidence_threshold: float = 0.75,
) -> dict:
    """Resolve blueprint type matching into an effective type and generation mode."""
    type_match = blueprint.get("type_match", {})
    strategy = blueprint.get("generation_strategy", {})
    recommended = str(type_match.get("recommended_type", "custom") or "custom")
    confidence = type_match.get("confidence", 0)
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        confidence = 0

    can_use_preset = (
        recommended in available_types
        and recommended != "custom"
        and confidence >= confidence_threshold
    )
    if can_use_preset:
        return {
            "effective_type": recommended,
            "generation_mode": "preset",
            "type_match_confidence": confidence,
            "type_match_overridden": False,
        }
    return {
        "effective_type": "custom",
        "generation_mode": "generic",
        "type_match_confidence": confidence,
        "type_match_overridden": recommended != "custom" or strategy.get("mode") != "generic",
    }
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_discovery_schema.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/discovery_schema.py tools/test_discovery_schema.py
git commit -m "feat: add expert blueprint schema helpers"
```

## Task 2: Custom Preset Compatibility

**Files:**
- Modify: `tools/expertise_presets.py`
- Modify: `tools/test_skill_writer.py`

- [ ] **Step 1: Write failing tests for the custom preset**

Add to `tools/test_skill_writer.py` near the existing expertise type tests:

```python
def test_custom_expertise_type_is_first_class_preset():
    types = {item["name"]: item for item in sw.list_expertise_types()}

    assert "custom" in types
    assert types["custom"]["knowledge_format"] == "blueprint_driven"
    assert types["custom"]["description"]


def test_create_custom_expert_without_type_specific_templates(tmp_path):
    base_dir, skill_dir = create_skill(
        tmp_path,
        slug="investment-committee",
        name="投委会专家",
        expertise_type="custom",
        domain_summary="投资项目评估、风险取舍与投委会决策。",
    )

    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
    heuristics = json.loads((skill_dir / "heuristics.json").read_text(encoding="utf-8"))

    assert meta["expertise_type"] == "custom"
    assert meta["preset"] == "expert.custom.v1"
    assert manifest["expertise_type"] == "custom"
    assert heuristics["knowledge_format"] == "blueprint_driven"
    assert "prompts/expertise/custom" not in json.dumps(manifest, ensure_ascii=False)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_skill_writer.py -k custom
```

Expected: FAIL with `KeyError` or missing `custom`.

- [ ] **Step 3: Add custom preset**

In `tools/expertise_presets.py`, add this entry to `EXPERTISE_PRESETS`:

```python
    "custom": {
        "name": "custom",
        "display_name": "Custom Expert",
        "identity_label": "蓝图驱动专家",
        "description": "根据专家能力蓝图动态生成，不依赖预置领域模板",
        "knowledge_format": "blueprint_driven",
        "execution_model": "blueprint_guided",
        "prompt_bundle": {
            "preset": "expert.custom.v1",
            "intake": "",
            "analyzer": "",
            "builder": "",
        },
        "intake_questions": [
            "这个专家主要解决什么问题？",
            "哪些场景最能体现他的判断能力？",
            "有哪些判断边界、反转条件或隐性取舍需要挖掘？",
        ],
        "knowledge_sections": [
            "适用场景",
            "核心工作流",
            "判断框架",
            "隐性知识目标",
            "边界条件",
            "经验教训",
        ],
        "storage_root": "skills/expert",
        "skill_name_prefix": "expert",
    },
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_skill_writer.py -k custom
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/expertise_presets.py tools/test_skill_writer.py
git commit -m "feat: add custom expert preset"
```

## Task 3: Blueprint Builder Tool

**Files:**
- Create: `prompts/discovery/expert_blueprint.md`
- Create: `tools/blueprint_builder.py`
- Create: `tools/test_blueprint_builder.py`

- [ ] **Step 1: Write failing tests for prompt assembly and parse-output**

Create `tools/test_blueprint_builder.py`:

```python
#!/usr/bin/env python3
"""Unit tests for blueprint_builder.py (P2.5 discovery phase)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import blueprint_builder as bb
from blueprint_builder import assemble_prompt, main


_MINIMAL_TEMPLATE = (
    "Name:{name}\nProfile:{expert_profile_json}\n"
    "Description:{user_description}\nMaterials:{material_summary}"
)


_SAMPLE_PROFILE = {
    "identity": {"name": "王五", "title": "投委", "domain": "投资决策"},
    "visible_knowledge": [{"rule": "先看下行风险", "source": "doc1"}],
    "known_decisions": [
        {"case": "A轮项目", "context": "增长快但现金流弱", "decision": "延后", "source": "doc1"},
        {"case": "并购项目", "context": "估值高但协同强", "decision": "推进", "source": "doc2"},
    ],
    "domain_context": {
        "key_challenges": ["信息不对称"],
        "common_pitfalls": ["只看增长"],
        "methodology_clashes": ["财务回报 vs 战略协同"],
    },
    "suspected_gaps": [{"gap": "退出路径", "reason": "材料没有说明退出判断"}],
}


def _valid_blueprint(confidence=0.61, recommended_type="decision_maker") -> dict:
    return {
        "identity_summary": {"name": "王五", "role": "投委会专家", "domain": "投资决策"},
        "domain_summary": "投资项目评估。",
        "primary_workflows": [{"name": "项目初筛"}, {"name": "投委会表决"}],
        "decision_scenarios": [
            {"scenario": "增长和现金流冲突"},
            {"scenario": "估值和协同冲突"},
            {"scenario": "团队和窗口期冲突"},
        ],
        "knowledge_shape": {"primary": "decision", "secondary": ["review"], "reason": "投资取舍"},
        "reasoning_framework": [{"name": "风险收益权衡", "description": "比较收益和下行"}],
        "tacit_knowledge_targets": [
            {"label": "窗口期", "description": "何时抢窗口"},
            {"label": "团队可信度", "description": "团队风险如何定价"},
            {"label": "退出确定性", "description": "退出路径权重"},
            {"label": "协同强度", "description": "战略协同补偿"},
            {"label": "风险可控性", "description": "条款是否能控风险"},
        ],
        "type_match": {
            "recommended_type": recommended_type,
            "confidence": confidence,
            "matched_signals": ["决策", "风险"],
            "rejected_types": [],
        },
        "generation_strategy": {
            "mode": "preset",
            "output_sections": ["适用场景", "判断框架", "边界条件"],
            "heuristics_shape": "decision_framework",
        },
        "scope_boundaries": [{"boundary": "不替代法律尽调"}],
        "evidence": ["profile.known_decisions[0]"],
    }


def _write_profile(tmp_path: Path) -> Path:
    base_dir = tmp_path / "skills" / "expert"
    discovery = base_dir / "wang-wu" / "discovery"
    discovery.mkdir(parents=True)
    (discovery / "expert_profile.json").write_text(
        json.dumps(_SAMPLE_PROFILE, ensure_ascii=False),
        encoding="utf-8",
    )
    return base_dir


class TestPromptAssembly(unittest.TestCase):
    def test_prompt_assembly_no_leftover_placeholders(self):
        import re
        result = assemble_prompt(
            template=_MINIMAL_TEMPLATE,
            name="王五",
            expert_profile_json='{"identity":{"name":"王五"}}',
            user_description="投委会专家",
            material_summary="访谈材料摘要",
        )
        self.assertEqual(re.findall(r"\{[a-z_]+\}", result), [])
        self.assertIn("王五", result)
        self.assertIn("投委会专家", result)


class TestBlueprintBuilderMain(unittest.TestCase):
    def setUp(self):
        self._orig = bb.PROMPT_TEMPLATE_PATH

    def tearDown(self):
        bb.PROMPT_TEMPLATE_PATH = self._orig

    def test_dry_run_conflicts_with_parse_output(self):
        rc = main(["--slug", "wang-wu", "--dry-run", "--parse-output", "out.json"])
        self.assertNotEqual(rc, 0)

    def test_parse_output_saves_blueprint_and_updates_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_dir = _write_profile(tmp_path)
            tpl = tmp_path / "tpl.md"
            tpl.write_text(_MINIMAL_TEMPLATE, encoding="utf-8")
            bb.PROMPT_TEMPLATE_PATH = tpl
            meta_path = base_dir / "wang-wu" / "meta.json"
            meta_path.write_text(json.dumps({"slug": "wang-wu", "discovery": {"status": "profile_ready"}}), encoding="utf-8")
            out = tmp_path / "out.json"
            out.write_text(json.dumps({"expert_blueprint": _valid_blueprint()}, ensure_ascii=False), encoding="utf-8")

            rc = main(["--slug", "wang-wu", "--base-dir", str(base_dir), "--parse-output", str(out)])

            self.assertEqual(rc, 0)
            saved = json.loads((base_dir / "wang-wu" / "discovery" / "expert_blueprint.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["type_match"]["recommended_type"], "decision_maker")
            self.assertEqual(saved["generation_strategy"]["mode"], "generic")
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertEqual(meta["discovery"]["status"], "blueprint_ready")
            self.assertEqual(meta["discovery"]["blueprint"]["effective_type"], "custom")
            self.assertTrue(meta["discovery"]["blueprint"]["type_match_overridden"])

    def test_high_confidence_builtin_keeps_preset_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_dir = _write_profile(tmp_path)
            tpl = tmp_path / "tpl.md"
            tpl.write_text(_MINIMAL_TEMPLATE, encoding="utf-8")
            bb.PROMPT_TEMPLATE_PATH = tpl
            out = tmp_path / "out.json"
            out.write_text(json.dumps({"expert_blueprint": _valid_blueprint(0.91, "decision_maker")}, ensure_ascii=False), encoding="utf-8")

            rc = main(["--slug", "wang-wu", "--base-dir", str(base_dir), "--parse-output", str(out)])

            self.assertEqual(rc, 0)
            saved = json.loads((base_dir / "wang-wu" / "discovery" / "expert_blueprint.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["generation_strategy"]["mode"], "preset")
            self.assertEqual(saved["type_match"]["effective_type"], "decision_maker")

    def test_invalid_blueprint_is_not_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_dir = _write_profile(tmp_path)
            tpl = tmp_path / "tpl.md"
            tpl.write_text(_MINIMAL_TEMPLATE, encoding="utf-8")
            bb.PROMPT_TEMPLATE_PATH = tpl
            invalid = _valid_blueprint()
            invalid["tacit_knowledge_targets"] = [{"label": "不足"}]
            out = tmp_path / "out.json"
            out.write_text(json.dumps({"expert_blueprint": invalid}, ensure_ascii=False), encoding="utf-8")

            rc = main(["--slug", "wang-wu", "--base-dir", str(base_dir), "--parse-output", str(out)])

            self.assertNotEqual(rc, 0)
            self.assertFalse((base_dir / "wang-wu" / "discovery" / "expert_blueprint.json").exists())
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_blueprint_builder.py
```

Expected: FAIL because `blueprint_builder.py` does not exist.

- [ ] **Step 3: Add prompt template**

Create `prompts/discovery/expert_blueprint.md` with sections for `{name}`, `{expert_profile_json}`, `{user_description}`, and `{material_summary}`. Include the exact JSON output object named `expert_blueprint` and require the fields from the spec: `identity_summary`, `domain_summary`, `primary_workflows`, `decision_scenarios`, `knowledge_shape`, `reasoning_framework`, `tacit_knowledge_targets`, `type_match`, `generation_strategy`, `scope_boundaries`, and `evidence`.

- [ ] **Step 4: Implement `tools/blueprint_builder.py`**

Create a P2.5 tool following the same pattern as `pre_researcher.py`. Define these public functions with the behavior below:

- `read_expert_profile(base_dir: str, slug: str) -> dict`: read `{base_dir}/{slug}/discovery/expert_profile.json`; raise `FileNotFoundError` with a message that says P2 must complete first.
- `read_optional_text(paths: list[Path]) -> str`: read each file as UTF-8 and join them with `\n\n`; return `""` when the list is empty.
- `assemble_prompt(template: str, name: str, expert_profile_json: str, user_description: str = "", material_summary: str = "") -> str`: replace `{name}`, `{expert_profile_json}`, `{user_description}`, and `{material_summary}`; use `（未填写）` or `（未提供）` for empty optional values.
- `_parse_output_file(output_path: Path) -> dict`: parse JSON first; accept either a top-level blueprint object or a wrapper object with the key `expert_blueprint`; then try YAML using the same optional PyYAML behavior as `pre_researcher.py`.
- `_resolve_and_apply_type_match(blueprint: dict) -> dict`: call `resolve_blueprint_type_match`, write `effective_type` and `type_match_overridden` under `blueprint["type_match"]`, and overwrite `blueprint["generation_strategy"]["mode"]` with the resolved generation mode.
- `_update_meta_json(meta_path: Path, resolved: dict) -> None`: if `meta.json` exists and is valid JSON, set `discovery.enabled=true`, `discovery.status="blueprint_ready"`, and write the `discovery.blueprint` summary block.
- `main(argv: list[str] | None = None) -> int`: implement the CLI flow described in this task and return `0` on success, `1` on validation or input errors.

Key implementation details:

```python
available_types = [item["name"] for item in list_expertise_types()]
resolved = resolve_blueprint_type_match(blueprint, available_types)
blueprint.setdefault("type_match", {})["effective_type"] = resolved["effective_type"]
blueprint["type_match"]["type_match_overridden"] = resolved["type_match_overridden"]
blueprint.setdefault("generation_strategy", {})["mode"] = resolved["generation_mode"]
```

The CLI arguments are:

```python
parser.add_argument("--slug", required=True)
parser.add_argument("--base-dir", default="./skills/expert", dest="base_dir")
parser.add_argument("--user-description", default="", dest="user_description")
parser.add_argument("--material-summary", nargs="+", metavar="FILE", default=[], dest="material_summary")
parser.add_argument("--parse-output", default="", metavar="FILE", dest="parse_output")
parser.add_argument("--dry-run", action="store_true", dest="dry_run")
```

- [ ] **Step 5: Run tests and verify they pass**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_blueprint_builder.py tools/test_discovery_schema.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add prompts/discovery/expert_blueprint.md tools/blueprint_builder.py tools/test_blueprint_builder.py
git commit -m "feat: add expert blueprint builder"
```

## Task 4: P3 Prompt Consumes Blueprint Seeds

**Files:**
- Modify: `tools/latent_variable_builder.py`
- Modify: `tools/test_latent_variable_builder.py`
- Modify: `prompts/discovery/latent_variable.md`

- [ ] **Step 1: Write failing tests for optional blueprint loading**

Add to `tools/test_latent_variable_builder.py`:

```python
def _write_blueprint(base_dir: Path, slug="zhang-san") -> None:
    blueprint = {
        "tacit_knowledge_targets": [
            {"label": "窗口期", "description": "何时接受估值溢价"},
            {"label": "团队可信度", "description": "团队风险如何定价"},
            {"label": "退出确定性", "description": "退出路径权重"},
            {"label": "协同强度", "description": "战略协同补偿"},
            {"label": "风险可控性", "description": "条款是否能控风险"},
        ],
        "decision_scenarios": [{"scenario": "增长和现金流冲突"}],
    }
    path = base_dir / slug / "discovery" / "expert_blueprint.json"
    path.write_text(json.dumps(blueprint, ensure_ascii=False), encoding="utf-8")


class TestBlueprintSeedsInPrompt(unittest.TestCase):
    def setUp(self):
        self._orig = lvb.PROMPT_TEMPLATE_PATH

    def tearDown(self):
        lvb.PROMPT_TEMPLATE_PATH = self._orig

    def test_prompt_includes_blueprint_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_dir = _write_profile(tmp_path)
            _write_blueprint(base_dir)
            tpl = tmp_path / "tpl.md"
            tpl.write_text("Expert:{name}\nProfile:{expert_profile_json}\nBlueprint:{expert_blueprint_json}", encoding="utf-8")
            lvb.PROMPT_TEMPLATE_PATH = tpl

            rc = main(["--slug", "zhang-san", "--base-dir", str(base_dir)])

            self.assertEqual(rc, 0)
            content = (base_dir / "zhang-san" / "discovery" / "latent_variable_prompt.md").read_text(encoding="utf-8")
            self.assertIn("窗口期", content)
            self.assertIn("expert_blueprint", content)

    def test_prompt_uses_not_provided_marker_when_blueprint_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_dir = _write_profile(tmp_path)
            tpl = tmp_path / "tpl.md"
            tpl.write_text("Blueprint:{expert_blueprint_json}", encoding="utf-8")
            lvb.PROMPT_TEMPLATE_PATH = tpl

            rc = main(["--slug", "zhang-san", "--base-dir", str(base_dir)])

            self.assertEqual(rc, 0)
            content = (base_dir / "zhang-san" / "discovery" / "latent_variable_prompt.md").read_text(encoding="utf-8")
            self.assertIn("（未提供）", content)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_latent_variable_builder.py -k BlueprintSeeds
```

Expected: FAIL because `{expert_blueprint_json}` is not replaced.

- [ ] **Step 3: Implement optional blueprint prompt input**

In `tools/latent_variable_builder.py`:

```python
def read_expert_blueprint(base_dir: str, slug: str) -> dict | None:
    path = Path(base_dir) / slug / "discovery" / "expert_blueprint.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
```

Update `assemble_prompt` signature to:

```python
def assemble_prompt(template: str, name: str, expertise_type: str, expert_profile_json: str, expert_blueprint_json: str = "（未提供）") -> str:
```

Add replacement:

```python
"{expert_blueprint_json}": expert_blueprint_json,
```

In `main`, read optional blueprint and pass:

```python
blueprint = read_expert_blueprint(args.base_dir, args.slug)
blueprint_json_str = (
    json.dumps({"expert_blueprint": blueprint}, ensure_ascii=False, indent=2)
    if blueprint is not None
    else "（未提供）"
)
```

- [ ] **Step 4: Update P3 prompt template**

In `prompts/discovery/latent_variable.md`, add after the expert profile input:

```markdown
### 专家能力蓝图（可选）
{expert_blueprint_json}
（来自 P2.5 expert_blueprint.md 的输出；如果未提供，请只使用 expert_profile）

如果提供了专家能力蓝图，优先把 `tacit_knowledge_targets` 作为候选来源种子，但仍必须输出标准的 `latent_variables` 结构，并且每个候选都要有可追溯证据。
```

- [ ] **Step 5: Run tests and verify they pass**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_latent_variable_builder.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/latent_variable_builder.py tools/test_latent_variable_builder.py prompts/discovery/latent_variable.md
git commit -m "feat: seed latent variables from expert blueprint"
```

## Task 5: P4 Prompt Consumes Blueprint Scenarios

**Files:**
- Modify: `tools/triplet_generator.py`
- Modify: `tools/test_triplet_generator.py`
- Modify: `prompts/discovery/triplet_builder.md`

- [ ] **Step 1: Write failing tests for blueprint scenario prompt input**

Add to `tools/test_triplet_generator.py`:

```python
def _write_blueprint(base_dir: Path, slug="zhang-san") -> None:
    blueprint = {
        "primary_workflows": [{"name": "投委会表决"}, {"name": "项目初筛"}],
        "decision_scenarios": [
            {"scenario": "增长快但现金流弱时是否推进"},
            {"scenario": "估值偏高但战略协同强时是否推进"},
            {"scenario": "团队经验不足但窗口期明确时是否推进"},
        ],
    }
    path = base_dir / slug / "discovery" / "expert_blueprint.json"
    path.write_text(json.dumps(blueprint, ensure_ascii=False), encoding="utf-8")


class TestBlueprintScenariosInPrompt(unittest.TestCase):
    def setUp(self):
        self._orig = tg.PROMPT_TEMPLATE_PATH

    def tearDown(self):
        tg.PROMPT_TEMPLATE_PATH = self._orig

    def test_prompt_includes_blueprint_scenarios_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_dir = _write_inputs(tmp_path)
            _write_blueprint(base_dir)
            tpl = tmp_path / "tpl.md"
            tpl.write_text(
                "Blueprint:{expert_blueprint_json}\nScenarios:{decision_scenarios_json}",
                encoding="utf-8",
            )
            tg.PROMPT_TEMPLATE_PATH = tpl

            rc = main(["--slug", "zhang-san", "--base-dir", str(base_dir)])

            self.assertEqual(rc, 0)
            content = (base_dir / "zhang-san" / "discovery" / "triplet_builder_prompt.md").read_text(encoding="utf-8")
            self.assertIn("投委会表决", content)
            self.assertIn("增长快但现金流弱", content)

    def test_prompt_uses_empty_scenarios_when_blueprint_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_dir = _write_inputs(tmp_path)
            tpl = tmp_path / "tpl.md"
            tpl.write_text("Scenarios:{decision_scenarios_json}", encoding="utf-8")
            tg.PROMPT_TEMPLATE_PATH = tpl

            rc = main(["--slug", "zhang-san", "--base-dir", str(base_dir)])

            self.assertEqual(rc, 0)
            content = (base_dir / "zhang-san" / "discovery" / "triplet_builder_prompt.md").read_text(encoding="utf-8")
            self.assertIn("[]", content)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_triplet_generator.py -k BlueprintScenarios
```

Expected: FAIL because the new placeholders are not replaced.

- [ ] **Step 3: Implement optional blueprint scenario input**

In `tools/triplet_generator.py`, add:

```python
def read_expert_blueprint(base_dir: str, slug: str) -> dict | None:
    path = Path(base_dir) / slug / "discovery" / "expert_blueprint.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
```

Update `assemble_prompt` to accept defaults:

```python
expert_blueprint_json: str = "（未提供）",
decision_scenarios_json: str = "[]",
```

Add replacements:

```python
"{expert_blueprint_json}": expert_blueprint_json,
"{decision_scenarios_json}": decision_scenarios_json,
```

In `main`:

```python
blueprint = read_expert_blueprint(args.base_dir, args.slug)
expert_blueprint_json = (
    json.dumps({"expert_blueprint": blueprint}, ensure_ascii=False, indent=2)
    if blueprint is not None
    else "（未提供）"
)
decision_scenarios_json = json.dumps(
    (blueprint or {}).get("decision_scenarios", []),
    ensure_ascii=False,
    indent=2,
)
```

- [ ] **Step 4: Update P4 prompt template**

In `prompts/discovery/triplet_builder.md`, add after known decisions:

```markdown
### 专家能力蓝图（可选）
{expert_blueprint_json}

### 蓝图决策场景（优先用于生态效度）
{decision_scenarios_json}

如果提供了蓝图，请优先使用 `decision_scenarios` 和 `primary_workflows` 设计 A/B/C 场景；如果未提供，继续使用 known_decisions 和 domain_context。
```

- [ ] **Step 5: Run tests and verify they pass**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_triplet_generator.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/triplet_generator.py tools/test_triplet_generator.py prompts/discovery/triplet_builder.md
git commit -m "feat: seed triplets from expert blueprint"
```

## Task 6: Generic Skill Renderer and P7 Integration

**Files:**
- Create: `tools/generic_skill_renderer.py`
- Modify: `tools/skill_writer.py`
- Modify: `tools/test_skill_writer.py`

- [ ] **Step 1: Write failing tests for generic rendering through skill writer**

Add to `tools/test_skill_writer.py`:

```python
SAMPLE_BLUEPRINT = {
    "identity_summary": {"name": "王五", "role": "投委会专家", "domain": "投资决策"},
    "domain_summary": "投资项目评估与投委会决策。",
    "primary_workflows": [{"name": "项目初筛"}, {"name": "投委会表决"}],
    "decision_scenarios": [
        {"scenario": "增长和现金流冲突"},
        {"scenario": "估值和协同冲突"},
        {"scenario": "团队和窗口期冲突"},
    ],
    "knowledge_shape": {"primary": "decision", "secondary": ["review"], "reason": "投资取舍"},
    "reasoning_framework": [{"name": "风险收益权衡", "description": "比较收益和下行"}],
    "tacit_knowledge_targets": [
        {"label": "窗口期", "description": "何时抢窗口"},
        {"label": "团队可信度", "description": "团队风险如何定价"},
        {"label": "退出确定性", "description": "退出路径权重"},
        {"label": "协同强度", "description": "战略协同补偿"},
        {"label": "风险可控性", "description": "条款是否能控风险"},
    ],
    "type_match": {"recommended_type": "decision_maker", "confidence": 0.61, "effective_type": "custom"},
    "generation_strategy": {
        "mode": "generic",
        "output_sections": ["适用场景", "核心工作流", "判断框架", "隐性知识目标", "边界条件"],
        "heuristics_shape": "decision_framework",
    },
    "scope_boundaries": [{"boundary": "不替代法律尽调"}],
    "evidence": ["profile.known_decisions[0]"],
}


def test_create_custom_expert_from_blueprint_generates_generic_artifacts(tmp_path):
    base_dir, skill_dir = create_skill(
        tmp_path,
        slug="investment-committee",
        name="投委会专家",
        expertise_type="custom",
        expertise_content="",
        domain_summary="投资项目评估。",
        blueprint=SAMPLE_BLUEPRINT,
    )

    expertise = (skill_dir / "expertise.md").read_text(encoding="utf-8")
    kg = (skill_dir / "knowledge_graph.md").read_text(encoding="utf-8")
    heuristics = json.loads((skill_dir / "heuristics.json").read_text(encoding="utf-8"))
    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))

    assert "## 专家能力蓝图" in expertise
    assert "项目初筛" in expertise
    assert "窗口期" in expertise
    assert "## 蓝图工作流" in kg
    assert heuristics["knowledge_format"] == "blueprint_driven"
    assert heuristics["blueprint"]["knowledge_shape"]["primary"] == "decision"
    assert meta["discovery"]["blueprint"]["effective_type"] == "custom"
    assert meta["discovery"]["blueprint"]["generation_mode"] == "generic"


def test_blueprint_cli_reads_json_file(tmp_path):
    blueprint_file = tmp_path / "blueprint.json"
    blueprint_file.write_text(json.dumps(SAMPLE_BLUEPRINT, ensure_ascii=False), encoding="utf-8")
    expertise_file = tmp_path / "expertise.md"
    expertise_file.write_text("", encoding="utf-8")
    base_dir = tmp_path / "skills" / "expert"

    rc = sw.main([
        "--action", "create",
        "--slug", "investment-committee",
        "--name", "投委会专家",
        "--expertise-type", "custom",
        "--expertise-content", str(expertise_file),
        "--blueprint", str(blueprint_file),
        "--base-dir", str(base_dir),
    ])

    assert rc is None
    expertise = (base_dir / "investment-committee" / "expertise.md").read_text(encoding="utf-8")
    assert "专家能力蓝图" in expertise
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_skill_writer.py -k "blueprint or generic"
```

Expected: FAIL because `write_expert_skill` has no `blueprint` argument and CLI has no `--blueprint`.

- [ ] **Step 3: Implement generic renderer**

Create `tools/generic_skill_renderer.py` with:

```python
from __future__ import annotations

import json


def _item_text(item: object, *keys: str) -> str:
    if isinstance(item, dict):
        for key in keys:
            if item.get(key):
                return str(item[key])
        return json.dumps(item, ensure_ascii=False)
    return str(item)


def render_generic_expertise(base_content: str, blueprint: dict) -> str:
    lines: list[str] = []
    if base_content.strip():
        lines.extend([base_content.rstrip(), ""])
    lines.extend(["## 专家能力蓝图", "", f"### 领域摘要", blueprint.get("domain_summary", "（未提供）"), ""])
    lines.extend(["### 核心工作流"])
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


def render_generic_heuristics(name: str, expertise_type: str, preset: dict, blueprint: dict) -> dict:
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
```

- [ ] **Step 4: Integrate renderer in `skill_writer.py`**

Add imports:

```python
from generic_skill_renderer import (
    render_generic_expertise,
    render_generic_heuristics,
    render_generic_knowledge_graph,
)
```

Add `blueprint: dict | None = None` to `write_expert_skill` and `update_expert_skill`.

Before applying latent section in `write_expert_skill`, add:

```python
use_generic_blueprint = (
    blueprint is not None
    and (expertise_type == "custom" or blueprint.get("generation_strategy", {}).get("mode") == "generic")
)
if use_generic_blueprint:
    expertise_content = render_generic_expertise(expertise_content, blueprint)
```

Before writing heuristics:

```python
if use_generic_blueprint:
    heuristics = render_generic_heuristics(name, expertise_type, preset, blueprint)
else:
    heuristics = {
        "expert": name,
        "expertise_type": expertise_type,
        "knowledge_format": preset["knowledge_format"],
        "execution_model": preset["execution_model"],
        "sections": preset["knowledge_sections"],
        "rules": [],
    }
```

For knowledge graph:

```python
kg_content = (
    render_generic_knowledge_graph(name, preset, blueprint)
    if use_generic_blueprint
    else generate_knowledge_graph_md(name, preset, discovery_meta)
)
```

Add a helper for meta:

```python
def _apply_blueprint_meta_fields(meta: dict, blueprint: dict | None) -> None:
    if blueprint is None:
        return
    d = meta.setdefault("discovery", {})
    d["enabled"] = True
    match = blueprint.get("type_match", {})
    strategy = blueprint.get("generation_strategy", {})
    d["blueprint"] = {
        "effective_type": match.get("effective_type", meta.get("expertise_type", "custom")),
        "generation_mode": strategy.get("mode", "generic"),
        "type_match_confidence": match.get("confidence", 0),
        "type_match_overridden": match.get("type_match_overridden", False),
        "type_forced_by_user": False,
    }
```

Call it after `_apply_discovery_meta_fields`.

Add CLI option and read JSON:

```python
parser.add_argument("--blueprint", default="", help="Path to expert_blueprint.json for generic/custom rendering")
```

```python
blueprint: dict | None = None
if args.blueprint:
    blueprint = json.loads(Path(args.blueprint).read_text(encoding="utf-8"))
```

Pass `blueprint=blueprint` to create/update.

Change the CLI entry signature from `def main():` to:

```python
def main(argv: list[str] | None = None):
```

and parse with:

```python
args = parser.parse_args(argv)
```

- [ ] **Step 5: Run tests and verify they pass**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_skill_writer.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/generic_skill_renderer.py tools/skill_writer.py tools/test_skill_writer.py
git commit -m "feat: render custom experts from blueprint"
```

## Task 7: Unknown-Domain End-to-End Smoke Test

**Files:**
- Create: `mock_expert_unknown/meta.json`
- Create: `mock_expert_unknown/discovery/expert_profile.json`
- Create: `mock_expert_unknown/discovery/expert_blueprint.json`
- Modify: `tools/test_e2e_mock.py`

- [ ] **Step 1: Create failing smoke test**

Add to `tools/test_e2e_mock.py`:

```python
UNKNOWN_DIR = Path(__file__).parent.parent / "mock_expert_unknown"
UNKNOWN_DISCOVERY = UNKNOWN_DIR / "discovery"


def test_unknown_domain_custom_blueprint_writes_skill(tmp_path):
    base_dir = str(tmp_path / "skills" / "expert")
    meta = _load_json(UNKNOWN_DIR / "meta.json")
    blueprint = _load_json(UNKNOWN_DISCOVERY / "expert_blueprint.json")

    sw.write_expert_skill(
        base_dir=base_dir,
        slug="investment-committee",
        name="投委会专家",
        expertise_type="custom",
        expertise_content="",
        domain_summary="投资项目评估、风险取舍与投委会决策。",
        meta=meta,
        blueprint=blueprint,
    )

    skill_dir = Path(base_dir) / "investment-committee"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "expertise.md").exists()
    assert (skill_dir / "heuristics.json").exists()
    assert (skill_dir / "knowledge_graph.md").exists()
    expertise = (skill_dir / "expertise.md").read_text(encoding="utf-8")
    heuristics = json.loads((skill_dir / "heuristics.json").read_text(encoding="utf-8"))
    assert "投委会表决" in expertise
    assert heuristics["expertise_type"] == "custom"
    assert heuristics["blueprint"]["tacit_knowledge_targets"]
```

- [ ] **Step 2: Run test and verify it fails because fixture is missing**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_e2e_mock.py -k unknown_domain
```

Expected: FAIL with missing `mock_expert_unknown`.

- [ ] **Step 3: Add unknown-domain fixtures**

Create `mock_expert_unknown/meta.json`:

```json
{
  "name": "投委会专家",
  "slug": "investment-committee",
  "expertise_type": "custom",
  "summary": "投委会专家，擅长投资项目评估、风险取舍与投委会决策",
  "discovery": {
    "enabled": true,
    "status": "blueprint_ready"
  }
}
```

Create `mock_expert_unknown/discovery/expert_profile.json`:

```json
{
  "identity": {
    "name": "王五",
    "title": "投委会专家",
    "domain": "投资决策",
    "years_in_field": 12
  },
  "visible_knowledge": [
    {
      "rule": "先看下行风险，再看增长弹性",
      "source": "investment_notes.md"
    },
    {
      "rule": "战略协同可以补偿短期财务指标不足",
      "source": "committee_minutes.md"
    },
    {
      "rule": "条款能控制的风险和条款不能控制的风险要分开判断",
      "source": "interview.md"
    }
  ],
  "known_decisions": [
    {
      "case": "A轮项目",
      "context": "增长快但现金流弱",
      "decision": "延后",
      "source": "investment_notes.md"
    },
    {
      "case": "并购项目",
      "context": "估值高但战略协同强",
      "decision": "推进",
      "source": "committee_minutes.md"
    }
  ],
  "domain_context": {
    "key_challenges": ["信息不对称", "退出路径不确定"],
    "common_pitfalls": ["只看增长", "忽略条款控制力"],
    "methodology_clashes": ["财务回报 vs 战略协同"]
  },
  "suspected_gaps": [
    {
      "gap": "退出路径权重",
      "reason": "材料多次讨论推进与延后，但没有说明退出确定性如何改变投票"
    },
    {
      "gap": "创始团队可信度阈值",
      "reason": "投资委员会通常讨论团队风险，材料只记录结论没有记录判断阈值"
    },
    {
      "gap": "估值溢价接受边界",
      "reason": "材料提到估值高仍推进，但没有说明溢价上限或反转条件"
    }
  ]
}
```

Create `mock_expert_unknown/discovery/expert_blueprint.json`:

```json
{
  "identity_summary": {
    "name": "王五",
    "role": "投委会专家",
    "domain": "投资决策"
  },
  "domain_summary": "投资项目评估、风险取舍与投委会决策。",
  "primary_workflows": [
    {"name": "项目初筛", "evidence": "profile.known_decisions[0]"},
    {"name": "投委会表决", "evidence": "profile.known_decisions[1]"}
  ],
  "decision_scenarios": [
    {"scenario": "增长快但现金流弱时是否推进", "evidence": "profile.known_decisions[0]"},
    {"scenario": "估值偏高但战略协同强时是否推进", "evidence": "profile.known_decisions[1]"},
    {"scenario": "团队经验不足但窗口期明确时是否推进", "evidence": "profile.suspected_gaps[1]"}
  ],
  "knowledge_shape": {
    "primary": "decision",
    "secondary": ["review"],
    "reason": "材料显示专家主要做投资项目评估和风险取舍。"
  },
  "reasoning_framework": [
    {"name": "风险收益权衡", "description": "比较下行风险与战略收益", "evidence": "profile.visible_knowledge[0]"},
    {"name": "条款控制力判断", "description": "判断风险是否可以通过条款限制", "evidence": "profile.visible_knowledge[2]"}
  ],
  "tacit_knowledge_targets": [
    {"label": "窗口期", "description": "何时接受估值溢价抢占战略窗口", "evidence": "profile.known_decisions[1]"},
    {"label": "团队可信度", "description": "创始团队缺口如何影响推进或延后", "evidence": "profile.suspected_gaps[1]"},
    {"label": "退出确定性", "description": "退出路径是否压倒短期增长", "evidence": "profile.suspected_gaps[0]"},
    {"label": "协同强度", "description": "战略协同对财务指标不足的补偿程度", "evidence": "profile.visible_knowledge[1]"},
    {"label": "风险可控性", "description": "风险是否可被条款控制", "evidence": "profile.visible_knowledge[2]"}
  ],
  "type_match": {
    "recommended_type": "decision_maker",
    "confidence": 0.61,
    "effective_type": "custom",
    "type_match_overridden": true,
    "matched_signals": ["投资决策", "风险取舍", "投委会表决"],
    "rejected_types": [{"type": "operator", "reason": "不是操作 SOP"}]
  },
  "generation_strategy": {
    "mode": "generic",
    "output_sections": ["适用场景", "核心工作流", "判断框架", "隐性知识目标", "边界条件"],
    "heuristics_shape": "decision_framework"
  },
  "scope_boundaries": [
    {"boundary": "不替代法律、财务或税务尽调", "evidence": "profile.visible_knowledge[2]"}
  ],
  "evidence": ["profile.known_decisions[0]", "profile.known_decisions[1]"]
}
```

- [ ] **Step 4: Run smoke tests**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q tools/test_e2e_mock.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mock_expert_unknown tools/test_e2e_mock.py
git commit -m "test: add unknown-domain blueprint smoke test"
```

## Task 8: Documentation Updates

**Files:**
- Modify: `README.md`
- Modify: `SKILL.md`

- [ ] **Step 1: Update README for blueprint-first creation**

In `README.md`, update "适合什么专家" to state:

```markdown
内置类型现在只是加速器，不再是创建专家的前置条件。创建流程可以先生成 `discovery/expert_blueprint.json`，根据材料判断是否匹配已有类型；匹配度不足时会使用 `custom` 通用专家蓝图继续生成。
```

Add `discovery/expert_blueprint.json` to the Discovery artifact list:

```markdown
- `discovery/expert_blueprint.json`：P2.5 专家能力蓝图，用于推断知识形态、类型匹配和 custom/generic 生成策略
```

Add a P2.5 command example after P2:

```bash
python tools/blueprint_builder.py \
  --slug demo-expert \
  --base-dir ./skills/expert \
  --user-description "擅长高压线上故障止血与容量判断"
```

Add parse-output example:

```bash
python tools/blueprint_builder.py \
  --slug demo-expert \
  --base-dir ./skills/expert \
  --parse-output ./tmp/expert_blueprint_output.json
```

- [ ] **Step 2: Update root SKILL.md for blueprint-first flow**

In `SKILL.md`, update the "专长类型" section to clarify:

```markdown
用户不需要提前选择或导入专家模板。先收集专家描述和材料，再生成专家能力蓝图；如果蓝图与内置类型高度匹配，则复用对应类型；否则使用 `custom` 通用专家结构。
```

Add P2.5 to the discovery flow with the same command examples as README.

- [ ] **Step 3: Run doc sanity checks**

Run:

```bash
rg -n "expert_blueprint|blueprint_builder|custom" README.md SKILL.md
```

Expected: output includes both files and all three terms.

- [ ] **Step 4: Commit**

```bash
git add README.md SKILL.md
git commit -m "docs: document blueprint-first expert creation"
```

## Task 9: Full Verification

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run full test suite**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Inspect worktree state**

Run:

```bash
git status --short
```

Expected: no uncommitted changes.

- [ ] **Step 3: Inspect branch history**

Run:

```bash
git log --oneline -10
```

Expected: separate commits exist for schema, custom preset, builder, P3, P4, renderer, smoke fixture, docs, and earlier spec/plan commits.

- [ ] **Step 4: Report verification**

Report the exact test result and branch path:

```text
Branch: blueprint-first-expert-skill
Worktree: /home/wzh/persona-skills/expert-skill/.worktrees/blueprint-first-expert-skill
Verification: UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q
```
