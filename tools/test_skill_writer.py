#!/usr/bin/env python3
"""Tests for P7 additions to tools/skill_writer.py"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import skill_writer as sw

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DISCOVERY_META = {
    "triplet_analyses": [
        {
            "triplet_id": "tg_001",
            "latent_findings": [
                {
                    "type": "变量",
                    "content": "隐性变量A",
                    "confidence": "high",
                    "evidence": {
                        "triplet_id": "tg_001",
                        "layer": "B",
                        "expert_quote": "专家说了什么",
                    },
                },
                {
                    "type": "变量",
                    "content": "隐性变量A",  # duplicate — should be de-duplicated
                    "confidence": "medium",
                    "evidence": {"triplet_id": "tg_001", "layer": "C", "expert_quote": "另一句话"},
                },
            ],
            "invalidated_candidates": ["lv_999"],
        }
    ],
    "cross_analysis": {
        "priority_topology": [
            {"winner": "规则A", "loser": "规则B", "condition": "条件X"}
        ],
        "boundary_map": [
            {
                "triplet_id": "tg_001",
                "boundary": "边界1",
                "applicable_domain": "场景A",
                "failure_domain": "场景B",
            }
        ],
    },
    "report_sections": {},
}

SAMPLE_DISCOVERY_META_WITH_RULE_REFS = {
    "triplet_analyses": [],
    "cross_analysis": {
        "priority_topology": [
            {
                "rule_A": "时间窗口约束（硬死线）",
                "rule_B": "止血效果最大化",
                "winner": "rule_A",
                "condition": "硬死线物理排除了更慢方案",
            },
            {
                "rule_A": "扩容（持续增长场景）",
                "rule_B": "限流（临时突发场景）",
                "winner": "取决于流量持续性",
                "condition": "持续增长且 CPU > 85% 时扩容主线，否则限流主线",
            },
        ],
        "boundary_map": [],
    },
    "report_sections": {},
}

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


def create_skill(tmp_path, slug="test-expert", **kwargs):
    """Helper: create a skill in tmp_path and return (base_dir, skill_dir)."""
    base_dir = str(tmp_path / "skills" / "expert")
    defaults = dict(
        base_dir=base_dir,
        slug=slug,
        name="测试专家",
        expertise_type="troubleshooter",
        expertise_content="专业知识内容。",
        domain_summary="领域摘要。",
    )
    defaults.update(kwargs)
    sw.write_expert_skill(**defaults)
    return base_dir, Path(base_dir) / slug


# ---------------------------------------------------------------------------
# 1. test_create_without_discovery_behavior_unchanged
# ---------------------------------------------------------------------------

def test_create_without_discovery_behavior_unchanged(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path)
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "expertise.md").exists()
    assert (skill_dir / "knowledge_graph.md").exists()
    assert (skill_dir / "heuristics.json").exists()
    assert (skill_dir / "meta.json").exists()
    assert (skill_dir / "manifest.json").exists()
    # No discovery artifacts created
    assert not (skill_dir / "latent_report.md").exists()
    assert not (skill_dir / "interview_transcript.md").exists()
    # heuristics has no latent fields
    h = json.loads((skill_dir / "heuristics.json").read_text(encoding="utf-8"))
    assert "latent_variables" not in h
    # meta.discovery.enabled is False
    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["discovery"]["enabled"] is False


# ---------------------------------------------------------------------------
# 2. test_update_without_discovery_behavior_unchanged
# ---------------------------------------------------------------------------

def test_update_without_discovery_behavior_unchanged(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path)
    original_meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    sw.update_expert_skill(base_dir=base_dir, slug="test-expert",
                           expertise_content="更新后的专业知识。")
    # expertise.md updated
    content = (skill_dir / "expertise.md").read_text(encoding="utf-8")
    assert "更新后的专业知识" in content
    # No discovery artifacts
    assert not (skill_dir / "latent_report.md").exists()
    # discovery.enabled still False
    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["discovery"]["enabled"] is False


# ---------------------------------------------------------------------------
# 3. test_list_command_still_works
# ---------------------------------------------------------------------------

def test_list_command_still_works(tmp_path):
    base_dir, _ = create_skill(tmp_path)
    experts = sw.list_experts(base_dir)
    assert len(experts) == 1
    assert experts[0]["slug"] == "test-expert"


# ---------------------------------------------------------------------------
# 4. test_write_latent_report_when_provided
# ---------------------------------------------------------------------------

def test_write_latent_report_when_provided(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, latent_report="# 隐性知识报告\n内容。")
    assert (skill_dir / "latent_report.md").exists()
    content = (skill_dir / "latent_report.md").read_text(encoding="utf-8")
    assert "隐性知识报告" in content


# ---------------------------------------------------------------------------
# 5. test_write_interview_transcript_when_provided
# ---------------------------------------------------------------------------

def test_write_interview_transcript_when_provided(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, interview_transcript="# 访谈记录\n内容。")
    assert (skill_dir / "interview_transcript.md").exists()
    content = (skill_dir / "interview_transcript.md").read_text(encoding="utf-8")
    assert "访谈记录" in content


# ---------------------------------------------------------------------------
# 6. test_heuristics_json_includes_latent_fields
# ---------------------------------------------------------------------------

def test_heuristics_json_includes_latent_fields(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, discovery_meta=SAMPLE_DISCOVERY_META)
    h = json.loads((skill_dir / "heuristics.json").read_text(encoding="utf-8"))
    assert "latent_variables" in h
    assert "priority_rules" in h
    assert "boundary_conditions" in h


# ---------------------------------------------------------------------------
# 7. test_latent_variables_deduplicated
# ---------------------------------------------------------------------------

def test_latent_variables_deduplicated(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, discovery_meta=SAMPLE_DISCOVERY_META)
    h = json.loads((skill_dir / "heuristics.json").read_text(encoding="utf-8"))
    contents = [v["content"] for v in h["latent_variables"]]
    assert contents.count("隐性变量A") == 1


# ---------------------------------------------------------------------------
# 8. test_knowledge_graph_md_has_real_content
# ---------------------------------------------------------------------------

def test_knowledge_graph_md_has_real_content(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, discovery_meta=SAMPLE_DISCOVERY_META)
    kg = (skill_dir / "knowledge_graph.md").read_text(encoding="utf-8")
    assert "## 隐性变量节点" in kg
    assert "## 规则冲突关系" in kg
    assert "## 边界条件" in kg
    # Should contain actual table rows
    assert "隐性变量A" in kg
    assert "规则A" in kg


def test_priority_rules_render_with_rule_refs_in_markdown(tmp_path):
    base_dir, skill_dir = create_skill(
        tmp_path,
        discovery_meta=SAMPLE_DISCOVERY_META_WITH_RULE_REFS,
    )
    expertise = (skill_dir / "expertise.md").read_text(encoding="utf-8")
    kg = (skill_dir / "knowledge_graph.md").read_text(encoding="utf-8")

    assert "时间窗口约束（硬死线） 优先于 止血效果最大化" in expertise
    assert "扩容（持续增长场景） 与 限流（临时突发场景） 的优先关系取决于流量持续性" in expertise
    assert "| 时间窗口约束（硬死线） | 止血效果最大化 |" in kg
    assert "| 取决于流量持续性 | 扩容（持续增长场景） / 限流（临时突发场景） |" in kg
    assert "rule_A 优先于" not in expertise
    assert "| rule_A |" not in kg


# ---------------------------------------------------------------------------
# 9. test_knowledge_graph_md_placeholder_without_discovery
# ---------------------------------------------------------------------------

def test_knowledge_graph_md_placeholder_without_discovery(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path)
    kg = (skill_dir / "knowledge_graph.md").read_text(encoding="utf-8")
    assert "知识图谱" in kg
    assert "专长类型" in kg
    # Should NOT contain the latent tables
    assert "## 隐性变量节点" not in kg


# ---------------------------------------------------------------------------
# 10. test_extract_latent_fields_from_analysis
# ---------------------------------------------------------------------------

def test_extract_latent_fields_from_analysis():
    fields = sw.extract_latent_fields(SAMPLE_DISCOVERY_META)
    assert isinstance(fields["latent_variables"], list)
    assert isinstance(fields["priority_rules"], list)
    assert isinstance(fields["boundary_conditions"], list)
    assert len(fields["latent_variables"]) == 1  # deduplicated
    assert fields["priority_rules"][0]["winner"] == "规则A"
    assert fields["boundary_conditions"][0]["boundary"] == "边界1"


# ---------------------------------------------------------------------------
# 11. test_manifest_includes_latent_report
# ---------------------------------------------------------------------------

def test_manifest_includes_latent_report(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, latent_report="报告内容")
    manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "latent_report.md" in manifest["artifacts"]


def test_medical_expertise_types_are_first_class_presets():
    types = {item["name"]: item for item in sw.list_expertise_types()}

    assert "clinical_care_manager" in types
    assert "care_operation_specialist" in types
    assert "medical_safety_reviewer" in types
    assert types["clinical_care_manager"]["knowledge_format"] == "clinical_care_framework"
    assert types["care_operation_specialist"]["knowledge_format"] == "care_operation_runbook"
    assert types["medical_safety_reviewer"]["knowledge_format"] == "medical_safety_checklist"


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

    assert base_dir.endswith("skills/expert")
    assert meta["expertise_type"] == "custom"
    assert meta["preset"] == "expert.custom.v1"
    assert manifest["expertise_type"] == "custom"
    assert heuristics["knowledge_format"] == "blueprint_driven"
    assert "prompts/expertise/custom" not in json.dumps(manifest, ensure_ascii=False)


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

    assert base_dir.endswith("skills/expert")
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


def test_create_medical_expert_uses_medical_type_without_legacy_mapping(tmp_path):
    base_dir, skill_dir = create_skill(
        tmp_path,
        slug="jiuan-chronic-metabolic",
        name="九安慢病代谢管理专家",
        expertise_type="clinical_care_manager",
        domain_summary="糖尿病、CGM、血压与心血管代谢风险管理。",
    )

    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
    heuristics = json.loads((skill_dir / "heuristics.json").read_text(encoding="utf-8"))
    skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

    assert base_dir.endswith("skills/expert")
    assert meta["expertise_type"] == "clinical_care_manager"
    assert meta["preset"] == "expert.medical.clinical_care_manager.v1"
    assert meta["id"] == "expert.clinical_care_manager.jiuan-chronic-metabolic"
    assert meta["classification"]["knowledge_format"] == "clinical_care_framework"
    assert meta["classification"]["execution_model"] == "clinical_care_management"
    assert manifest["expertise_type"] == "clinical_care_manager"
    assert manifest["preset"] == "expert.medical.clinical_care_manager.v1"
    assert manifest["engine"]["prompt_bundle"]["intake"] == (
        "prompts/expertise/medical/clinical_care_manager/intake.md"
    )
    assert heuristics["sections"] == [
        "适用人群与场景",
        "关键健康指标",
        "风险分层",
        "干预路径",
        "升级医生规则",
        "禁忌与安全边界",
    ]

    serialized = json.dumps(
        {"meta": meta, "manifest": manifest, "heuristics": heuristics},
        ensure_ascii=False,
    )
    assert "troubleshooter" not in serialized
    assert "operator" not in serialized
    assert "reviewer" not in serialized
    assert "诊断/设计/审查/决策/操作" not in skill_md
    assert "升级建议" in skill_md


# ---------------------------------------------------------------------------
# 12. test_manifest_includes_interview_transcript
# ---------------------------------------------------------------------------

def test_manifest_includes_interview_transcript(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, interview_transcript="访谈内容")
    manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "interview_transcript.md" in manifest["artifacts"]


# ---------------------------------------------------------------------------
# 13. test_p7_gate_latent_knowledge_in_heuristics
# ---------------------------------------------------------------------------

def test_p7_gate_latent_knowledge_in_heuristics(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, discovery_meta=SAMPLE_DISCOVERY_META)
    h = json.loads((skill_dir / "heuristics.json").read_text(encoding="utf-8"))
    # At least one of the latent fields should be non-empty
    assert h["latent_variables"] or h["priority_rules"] or h["boundary_conditions"]
    assert len(h["latent_variables"]) == 1
    assert len(h["priority_rules"]) == 1
    assert len(h["boundary_conditions"]) == 1


# ---------------------------------------------------------------------------
# 14. test_discovery_artifacts_enable_meta_discovery
# ---------------------------------------------------------------------------

def test_discovery_artifacts_enable_meta_discovery(tmp_path):
    # Test with latent_report
    base_dir, skill_dir = create_skill(tmp_path, latent_report="报告内容")
    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["discovery"]["enabled"] is True

    # Test with interview_transcript (fresh skill)
    base_dir2, skill_dir2 = create_skill(tmp_path, slug="test-expert-2",
                                         interview_transcript="访谈内容")
    meta2 = json.loads((skill_dir2 / "meta.json").read_text(encoding="utf-8"))
    assert meta2["discovery"]["enabled"] is True

    # Test with discovery_meta
    base_dir3, skill_dir3 = create_skill(tmp_path, slug="test-expert-3",
                                         discovery_meta=SAMPLE_DISCOVERY_META)
    meta3 = json.loads((skill_dir3 / "meta.json").read_text(encoding="utf-8"))
    assert meta3["discovery"]["enabled"] is True


# ---------------------------------------------------------------------------
# 15. test_discovery_meta_sets_analysis_completed
# ---------------------------------------------------------------------------

def test_discovery_meta_sets_analysis_completed(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, discovery_meta=SAMPLE_DISCOVERY_META)
    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["discovery"]["analysis_completed"] is True


# ---------------------------------------------------------------------------
# 16. test_latent_report_sets_report_generated
# ---------------------------------------------------------------------------

def test_latent_report_sets_report_generated(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, latent_report="报告内容")
    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["discovery"]["report_generated"] is True


# ---------------------------------------------------------------------------
# 17. test_expertise_md_includes_latent_knowledge_section
# ---------------------------------------------------------------------------

def test_expertise_md_includes_latent_knowledge_section(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, discovery_meta=SAMPLE_DISCOVERY_META)
    expertise = (skill_dir / "expertise.md").read_text(encoding="utf-8")
    skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "## 隐性知识增强" in expertise
    assert "## 隐性知识增强" in skill_md


# ---------------------------------------------------------------------------
# 18. test_update_rebuilds_manifest_with_discovery_artifacts
# ---------------------------------------------------------------------------

def test_update_rebuilds_manifest_with_discovery_artifacts(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path)
    # Before update: discovery not enabled, manifest shouldn't have discovery artifacts
    manifest_before = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "latent_report.md" not in manifest_before["artifacts"]

    # Update with discovery params
    sw.update_expert_skill(base_dir=base_dir, slug="test-expert",
                           latent_report="报告内容",
                           discovery_meta=SAMPLE_DISCOVERY_META)

    manifest_after = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "latent_report.md" in manifest_after["artifacts"]
    assert "discovery" in manifest_after["capabilities"]


# ---------------------------------------------------------------------------
# 19. test_extract_latent_fields_accepts_english_variable_type
# ---------------------------------------------------------------------------

def test_extract_latent_fields_accepts_english_variable_type():
    meta = {
        "triplet_analyses": [
            {
                "triplet_id": "tg_001",
                "latent_findings": [
                    {"type": "variable", "content": "英文变量类型A",
                     "confidence": "high", "evidence": {}},
                    {"type": "latent_variable", "content": "英文变量类型B",
                     "confidence": "medium", "evidence": {}},
                    {"type": "优先级", "content": "非变量类型",  # should NOT be included
                     "confidence": "low", "evidence": {}},
                ],
            }
        ],
        "cross_analysis": {"priority_topology": [], "boundary_map": []},
    }
    fields = sw.extract_latent_fields(meta)
    contents = [v["content"] for v in fields["latent_variables"]]
    assert "英文变量类型A" in contents
    assert "英文变量类型B" in contents
    assert "非变量类型" not in contents


# ---------------------------------------------------------------------------
# 20. test_interview_transcript_cli_reads_markdown
# ---------------------------------------------------------------------------

def test_interview_transcript_cli_reads_markdown(tmp_path):
    # Write a fake interview_transcript.md file
    transcript_file = tmp_path / "interview_transcript.md"
    transcript_file.write_text("# 访谈记录\n专家原话内容。", encoding="utf-8")

    base_dir = str(tmp_path / "skills" / "expert")
    sw.main.__module__  # ensure imported

    import sys as _sys
    old_argv = _sys.argv
    try:
        _sys.argv = [
            "skill_writer.py",
            "--action", "create",
            "--slug", "cli-test",
            "--name", "CLI测试专家",
            "--base-dir", base_dir,
            "--interview-transcript", str(transcript_file),
        ]
        sw.main()
    finally:
        _sys.argv = old_argv

    skill_dir = Path(base_dir) / "cli-test"
    assert (skill_dir / "interview_transcript.md").exists()
    content = (skill_dir / "interview_transcript.md").read_text(encoding="utf-8")
    assert "访谈记录" in content


# ---------------------------------------------------------------------------
# 21. test_latent_section_appended_before_writing_files
# ---------------------------------------------------------------------------

def test_latent_section_appended_before_writing_files(tmp_path):
    base_content = "原始专业知识内容。"
    base_dir, skill_dir = create_skill(tmp_path,
                                       expertise_content=base_content,
                                       discovery_meta=SAMPLE_DISCOVERY_META)
    expertise = (skill_dir / "expertise.md").read_text(encoding="utf-8")
    skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    # Both files should have original content AND the latent section
    assert "原始专业知识内容" in expertise
    assert "## 隐性知识增强" in expertise
    assert "原始专业知识内容" in skill_md
    assert "## 隐性知识增强" in skill_md


# ---------------------------------------------------------------------------
# 22. test_latent_section_not_duplicated_on_update
# ---------------------------------------------------------------------------

def test_latent_section_not_duplicated_on_update(tmp_path):
    # First create with discovery_meta → section added
    base_dir, skill_dir = create_skill(tmp_path, discovery_meta=SAMPLE_DISCOVERY_META)

    # Update again with discovery_meta → section must NOT be duplicated
    sw.update_expert_skill(base_dir=base_dir, slug="test-expert",
                           discovery_meta=SAMPLE_DISCOVERY_META)

    expertise = (skill_dir / "expertise.md").read_text(encoding="utf-8")
    count = expertise.count("## 隐性知识增强")
    assert count == 1


def test_latent_section_refreshed_on_update(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, discovery_meta=SAMPLE_DISCOVERY_META)

    refreshed_meta = {
        **SAMPLE_DISCOVERY_META,
        "cross_analysis": {
            "priority_topology": [
                {
                    "rule_A": "时间窗口约束（硬死线）",
                    "rule_B": "止血效果最大化",
                    "winner": "rule_A",
                    "condition": "硬死线物理排除了更慢方案",
                }
            ],
            "boundary_map": [],
        },
    }
    sw.update_expert_skill(
        base_dir=base_dir,
        slug="test-expert",
        discovery_meta=refreshed_meta,
    )

    expertise = (skill_dir / "expertise.md").read_text(encoding="utf-8")
    assert "时间窗口约束（硬死线） 优先于 止血效果最大化" in expertise
    assert "规则A" not in expertise


# ---------------------------------------------------------------------------
# 23. test_manifest_with_only_discovery_meta_does_not_list_missing_report_or_transcript
# ---------------------------------------------------------------------------

def test_manifest_with_only_discovery_meta_does_not_list_missing_report_or_transcript(tmp_path):
    # Only discovery_meta provided; no latent_report or interview_transcript
    base_dir, skill_dir = create_skill(tmp_path, discovery_meta=SAMPLE_DISCOVERY_META)
    manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
    # Neither file is actually written, so manifest must not declare them
    assert "latent_report.md" not in manifest["artifacts"]
    assert "interview_transcript.md" not in manifest["artifacts"]
    # But discovery capability should still be present
    assert "discovery" in manifest["capabilities"]


# ---------------------------------------------------------------------------
# 24. test_manifest_lists_latent_report_only_when_report_written
# ---------------------------------------------------------------------------

def test_manifest_lists_latent_report_only_when_report_written(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, latent_report="报告内容")
    manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "latent_report.md" in manifest["artifacts"]
    assert "interview_transcript.md" not in manifest["artifacts"]


# ---------------------------------------------------------------------------
# 25. test_manifest_lists_interview_transcript_only_when_transcript_written
# ---------------------------------------------------------------------------

def test_manifest_lists_interview_transcript_only_when_transcript_written(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, interview_transcript="访谈内容")
    manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "interview_transcript.md" in manifest["artifacts"]
    assert "latent_report.md" not in manifest["artifacts"]


# ---------------------------------------------------------------------------
# 26. test_discovery_capability_present_when_only_discovery_meta_provided
# ---------------------------------------------------------------------------

def test_discovery_capability_present_when_only_discovery_meta_provided(tmp_path):
    base_dir, skill_dir = create_skill(tmp_path, discovery_meta=SAMPLE_DISCOVERY_META)
    manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "discovery" in manifest["capabilities"]
    assert "expertise" in manifest["capabilities"]


# ---------------------------------------------------------------------------
# 27. test_discovery_meta_does_not_advance_status_from_not_started
# ---------------------------------------------------------------------------

def test_discovery_meta_does_not_advance_status_from_not_started(tmp_path):
    # skill_writer.py must NOT auto-advance status to "analysis_ready"
    initial_meta = {
        "name": "Test Expert",
        "slug": "test-expert",
        "expertise_type": "troubleshooter",
        "discovery": {"status": "not_started", "enabled": False},
    }
    base_dir, skill_dir = create_skill(
        tmp_path, meta=initial_meta, discovery_meta=SAMPLE_DISCOVERY_META
    )
    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    # Status must not have been advanced by skill_writer
    assert meta["discovery"]["status"] == "not_started"
    # But enabled and analysis_completed should be set
    assert meta["discovery"]["enabled"] is True
    assert meta["discovery"]["analysis_completed"] is True


# ---------------------------------------------------------------------------
# 28. test_discovery_artifacts_do_not_overwrite_existing_status
# ---------------------------------------------------------------------------

def test_discovery_artifacts_do_not_overwrite_existing_status(tmp_path):
    initial_meta = {
        "name": "Test Expert",
        "slug": "test-expert",
        "expertise_type": "troubleshooter",
        "discovery": {"status": "interview_completed", "enabled": True},
    }
    base_dir, skill_dir = create_skill(
        tmp_path, meta=initial_meta,
        latent_report="报告内容",
        interview_transcript="访谈内容",
        discovery_meta=SAMPLE_DISCOVERY_META,
    )
    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    # Existing status must be preserved — skill_writer must not overwrite it
    assert meta["discovery"]["status"] == "interview_completed"
