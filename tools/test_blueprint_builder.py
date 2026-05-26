#!/usr/bin/env python3
"""Unit tests for blueprint_builder.py (P2.5 discovery phase)."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import blueprint_builder as bb
from blueprint_builder import assemble_prompt, main


_MINIMAL_TEMPLATE = (
    "Name:{name}\nProfile:{expert_profile_json}\n"
    "Description:{user_description}\nMaterials:{material_summary}\nTypes:{expertise_types_json}"
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
        self.assertIn("访谈材料摘要", result)

    def test_prompt_assembly_includes_expertise_types(self):
        result = assemble_prompt(
            template=_MINIMAL_TEMPLATE,
            name="王五",
            expert_profile_json="{}",
        )
        self.assertNotIn("{expertise_types_json}", result)
        self.assertIn("decision_maker", result)
        self.assertIn("custom", result)

    def test_read_optional_text_labels_each_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            first = tmp_path / "summary-a.md"
            second = tmp_path / "summary-b.md"
            first.write_text("第一份摘要", encoding="utf-8")
            second.write_text("第二份摘要", encoding="utf-8")

            result = bb.read_optional_text([first, second])

            self.assertIn("--- summary-a.md ---\n第一份摘要", result)
            self.assertIn("--- summary-b.md ---\n第二份摘要", result)


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
            meta_path.write_text(
                json.dumps({"slug": "wang-wu", "discovery": {"status": "profile_ready"}}),
                encoding="utf-8",
            )
            out = tmp_path / "out.json"
            out.write_text(
                json.dumps({"expert_blueprint": _valid_blueprint()}, ensure_ascii=False),
                encoding="utf-8",
            )

            rc = main(["--slug", "wang-wu", "--base-dir", str(base_dir), "--parse-output", str(out)])

            self.assertEqual(rc, 0)
            saved = json.loads(
                (base_dir / "wang-wu" / "discovery" / "expert_blueprint.json").read_text(encoding="utf-8")
            )
            self.assertEqual(saved["type_match"]["recommended_type"], "decision_maker")
            self.assertEqual(saved["generation_strategy"]["mode"], "generic")
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertTrue(meta["discovery"]["enabled"])
            self.assertEqual(meta["discovery"]["status"], "blueprint_ready")
            self.assertEqual(meta["discovery"]["blueprint"]["path"], "discovery/expert_blueprint.json")
            self.assertEqual(meta["discovery"]["blueprint"]["effective_type"], "custom")
            self.assertEqual(meta["discovery"]["blueprint"]["generation_mode"], "generic")
            self.assertEqual(meta["discovery"]["blueprint"]["type_match_confidence"], 0.61)
            self.assertTrue(meta["discovery"]["blueprint"]["type_match_overridden"])
            self.assertFalse(meta["discovery"]["blueprint"]["type_forced_by_user"])

    def test_parse_output_preserves_later_meta_status_and_updates_blueprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_dir = _write_profile(tmp_path)
            tpl = tmp_path / "tpl.md"
            tpl.write_text(_MINIMAL_TEMPLATE, encoding="utf-8")
            bb.PROMPT_TEMPLATE_PATH = tpl
            meta_path = base_dir / "wang-wu" / "meta.json"
            meta_path.write_text(
                json.dumps({"slug": "wang-wu", "discovery": {"status": "variables_ready"}}),
                encoding="utf-8",
            )
            out = tmp_path / "out.json"
            out.write_text(
                json.dumps({"expert_blueprint": _valid_blueprint(0.91, "decision_maker")}, ensure_ascii=False),
                encoding="utf-8",
            )

            rc = main(["--slug", "wang-wu", "--base-dir", str(base_dir), "--parse-output", str(out)])

            self.assertEqual(rc, 0)
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertEqual(meta["discovery"]["status"], "variables_ready")
            self.assertEqual(meta["discovery"]["blueprint"]["effective_type"], "decision_maker")
            self.assertEqual(meta["discovery"]["blueprint"]["generation_mode"], "preset")

    def test_material_summary_files_are_labelled_in_generated_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_dir = _write_profile(tmp_path)
            tpl = tmp_path / "tpl.md"
            tpl.write_text(_MINIMAL_TEMPLATE, encoding="utf-8")
            bb.PROMPT_TEMPLATE_PATH = tpl
            first = tmp_path / "notes-a.md"
            second = tmp_path / "notes-b.md"
            first.write_text("材料 A", encoding="utf-8")
            second.write_text("材料 B", encoding="utf-8")

            rc = main(
                [
                    "--slug",
                    "wang-wu",
                    "--base-dir",
                    str(base_dir),
                    "--material-summary",
                    str(first),
                    str(second),
                ]
            )

            self.assertEqual(rc, 0)
            prompt = (base_dir / "wang-wu" / "discovery" / "expert_blueprint_prompt.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("--- notes-a.md ---\n材料 A", prompt)
            self.assertIn("--- notes-b.md ---\n材料 B", prompt)

    def test_low_confidence_builtin_recommendation_downgrades_to_custom_generic(self):
        resolved = bb._resolve_and_apply_type_match(_valid_blueprint(0.61, "decision_maker"))

        self.assertEqual(resolved["type_match"]["effective_type"], "custom")
        self.assertTrue(resolved["type_match"]["type_match_overridden"])
        self.assertEqual(resolved["generation_strategy"]["mode"], "generic")

    def test_high_confidence_builtin_keeps_preset_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_dir = _write_profile(tmp_path)
            tpl = tmp_path / "tpl.md"
            tpl.write_text(_MINIMAL_TEMPLATE, encoding="utf-8")
            bb.PROMPT_TEMPLATE_PATH = tpl
            out = tmp_path / "out.json"
            out.write_text(
                json.dumps({"expert_blueprint": _valid_blueprint(0.91, "decision_maker")}, ensure_ascii=False),
                encoding="utf-8",
            )

            rc = main(["--slug", "wang-wu", "--base-dir", str(base_dir), "--parse-output", str(out)])

            self.assertEqual(rc, 0)
            saved = json.loads(
                (base_dir / "wang-wu" / "discovery" / "expert_blueprint.json").read_text(encoding="utf-8")
            )
            self.assertEqual(saved["generation_strategy"]["mode"], "preset")
            self.assertEqual(saved["type_match"]["effective_type"], "decision_maker")
            self.assertFalse(saved["type_match"]["type_match_overridden"])

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


if __name__ == "__main__":
    unittest.main()
