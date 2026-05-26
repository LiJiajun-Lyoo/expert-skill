#!/usr/bin/env python3
"""
Expertise preset registry for the enterprise-expert-skill engine.

Defines expertise types as the primary abstraction dimension.
Each expertise type has its own intake questions, knowledge format,
and execution model — orthogonal to who the expert is.
"""

from __future__ import annotations


EXPERTISE_PRESETS = {
    "troubleshooter": {
        "name": "troubleshooter",
        "display_name": "Troubleshooter",
        "identity_label": "诊断专家",
        "description": "擅长故障诊断与排查，能从现象快速定位根因",
        "knowledge_format": "decision_tree",
        "execution_model": "diagnostic",
        "prompt_bundle": {
            "preset": "expert.troubleshooter.v1",
            "intake": "prompts/expertise/troubleshooter/intake.md",
            "analyzer": "prompts/expertise/troubleshooter/analyzer.md",
            "builder": "prompts/expertise/troubleshooter/builder.md",
        },
        "intake_questions": [
            "你主要负责排查哪些类型的系统/问题？",
            "遇到陌生故障时，你的第一步通常是什么？",
            "你有哪些'一上来就查'的固定检查项？",
        ],
        "knowledge_sections": [
            "常见故障模式",
            "诊断决策链",
            "嗅觉检查项 (smell tests)",
            "工具与命令",
            "经验教训",
        ],
        "storage_root": "skills/expert",
        "skill_name_prefix": "expert",
    },
    "architect": {
        "name": "architect",
        "display_name": "Architect",
        "identity_label": "架构专家",
        "description": "擅长系统设计与技术选型，能从全局视角做出架构决策",
        "knowledge_format": "design_principles",
        "execution_model": "evaluative",
        "prompt_bundle": {
            "preset": "expert.architect.v1",
            "intake": "prompts/expertise/architect/intake.md",
            "analyzer": "prompts/expertise/architect/analyzer.md",
            "builder": "prompts/expertise/architect/builder.md",
        },
        "intake_questions": [
            "你主要设计哪些类型的系统？",
            "做技术选型时你最优先考虑什么？",
            "你有哪些'绝对不能这样设计'的红线？",
        ],
        "knowledge_sections": [
            "设计原则",
            "技术选型矩阵",
            "反模式与红线",
            "架构决策记录 (ADR)",
            "经验教训",
        ],
        "storage_root": "skills/expert",
        "skill_name_prefix": "expert",
    },
    "reviewer": {
        "name": "reviewer",
        "display_name": "Reviewer",
        "identity_label": "审核专家",
        "description": "擅长代码/方案审查，能快速发现缺陷与风险点",
        "knowledge_format": "checklist",
        "execution_model": "evaluative",
        "prompt_bundle": {
            "preset": "expert.reviewer.v1",
            "intake": "prompts/expertise/reviewer/intake.md",
            "analyzer": "prompts/expertise/reviewer/analyzer.md",
            "builder": "prompts/expertise/reviewer/builder.md",
        },
        "intake_questions": [
            "你主要 Review 哪些类型的内容（代码/方案/架构）？",
            "Review 时你最关注什么？",
            "你有哪些'一看到就会 block'的模式？",
        ],
        "knowledge_sections": [
            "缺陷模式库",
            "Review 检查清单",
            "风险等级判定",
            "常见争议与处理方式",
            "经验教训",
        ],
        "storage_root": "skills/expert",
        "skill_name_prefix": "expert",
    },
    "decision_maker": {
        "name": "decision_maker",
        "display_name": "Decision Maker",
        "identity_label": "决策专家",
        "description": "擅长在不确定条件下做权衡与优先级判断",
        "knowledge_format": "decision_framework",
        "execution_model": "evaluative",
        "prompt_bundle": {
            "preset": "expert.decision_maker.v1",
            "intake": "prompts/expertise/decision_maker/intake.md",
            "analyzer": "prompts/expertise/decision_maker/analyzer.md",
            "builder": "prompts/expertise/decision_maker/builder.md",
        },
        "intake_questions": [
            "你主要做哪些类型的决策？",
            "做决策时你的核心判断框架是什么？",
            "什么情况下你会推迟决策或向上求助？",
        ],
        "knowledge_sections": [
            "决策框架",
            "风险评估矩阵",
            "优先级排序方法",
            "历史决策与复盘",
            "经验教训",
        ],
        "storage_root": "skills/expert",
        "skill_name_prefix": "expert",
    },
    "operator": {
        "name": "operator",
        "display_name": "Operator",
        "identity_label": "运维专家",
        "description": "擅长系统运维与稳定性保障，掌握大量操作经验与监控阈值",
        "knowledge_format": "runbook",
        "execution_model": "procedural",
        "prompt_bundle": {
            "preset": "expert.operator.v1",
            "intake": "prompts/expertise/operator/intake.md",
            "analyzer": "prompts/expertise/operator/analyzer.md",
            "builder": "prompts/expertise/operator/builder.md",
        },
        "intake_questions": [
            "你负责运维哪些系统？",
            "日常巡检你最关注什么指标？",
            "紧急情况下你的标准操作流程是什么？",
        ],
        "knowledge_sections": [
            "监控指标与阈值",
            "标准操作流程 (SOP)",
            "升级规则",
            "常见事故处理",
            "经验教训",
        ],
        "storage_root": "skills/expert",
        "skill_name_prefix": "expert",
    },
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
    "clinical_care_manager": {
        "name": "clinical_care_manager",
        "display_name": "Clinical Care Manager",
        "identity_label": "临床照护管理专家",
        "description": "擅长慢病临床照护管理，能围绕关键指标、风险分层和升级规则给出判断框架",
        "knowledge_format": "clinical_care_framework",
        "execution_model": "clinical_care_management",
        "prompt_bundle": {
            "preset": "expert.medical.clinical_care_manager.v1",
            "intake": "prompts/expertise/medical/clinical_care_manager/intake.md",
            "analyzer": "prompts/expertise/medical/clinical_care_manager/analyzer.md",
            "builder": "prompts/expertise/medical/clinical_care_manager/builder.md",
        },
        "intake_questions": [
            "你主要管理哪些慢病或代谢类问题？",
            "做风险分层时，你最先看哪些关键指标和趋势？",
            "什么情况下必须升级给医生、转诊或提示急诊？",
        ],
        "knowledge_sections": [
            "适用人群与场景",
            "关键健康指标",
            "风险分层",
            "干预路径",
            "升级医生规则",
            "禁忌与安全边界",
        ],
        "storage_root": "skills/expert",
        "skill_name_prefix": "medical_expert",
    },
    "care_operation_specialist": {
        "name": "care_operation_specialist",
        "display_name": "Care Operation Specialist",
        "identity_label": "照护运营专家",
        "description": "擅长慢病照护执行与运营，能沉淀随访、患者教育、依从性管理和照护记录 SOP",
        "knowledge_format": "care_operation_runbook",
        "execution_model": "care_operation",
        "prompt_bundle": {
            "preset": "expert.medical.care_operation_specialist.v1",
            "intake": "prompts/expertise/medical/care_operation_specialist/intake.md",
            "analyzer": "prompts/expertise/medical/care_operation_specialist/analyzer.md",
            "builder": "prompts/expertise/medical/care_operation_specialist/builder.md",
        },
        "intake_questions": [
            "你负责哪些照护流程和患者运营动作？",
            "一次标准随访从准备到记录的完整 SOP 是什么？",
            "遇到患者依从性差、数据缺失或异常反馈时如何处理？",
        ],
        "knowledge_sections": [
            "照护流程 SOP",
            "随访与记录规范",
            "饮食运动干预",
            "患者教育",
            "依从性管理",
            "任务优先级与升级",
        ],
        "storage_root": "skills/expert",
        "skill_name_prefix": "medical_expert",
    },
    "medical_safety_reviewer": {
        "name": "medical_safety_reviewer",
        "display_name": "Medical Safety Reviewer",
        "identity_label": "医疗安全审核专家",
        "description": "擅长医疗输出安全审核，能识别红旗症状、用药风险、禁忌建议和升级边界",
        "knowledge_format": "medical_safety_checklist",
        "execution_model": "medical_safety_review",
        "prompt_bundle": {
            "preset": "expert.medical.medical_safety_reviewer.v1",
            "intake": "prompts/expertise/medical/medical_safety_reviewer/intake.md",
            "analyzer": "prompts/expertise/medical/medical_safety_reviewer/analyzer.md",
            "builder": "prompts/expertise/medical/medical_safety_reviewer/builder.md",
        },
        "intake_questions": [
            "你主要审核哪些医疗建议或患者沟通内容？",
            "哪些红旗症状、用药风险或禁忌建议必须阻断输出？",
            "你如何判断一条建议需要医生确认、转诊或急诊提示？",
        ],
        "knowledge_sections": [
            "审核范围",
            "红旗症状",
            "用药与低血糖风险",
            "禁忌建议",
            "升级与转诊规则",
            "合规表达边界",
        ],
        "storage_root": "skills/expert",
        "skill_name_prefix": "medical_expert",
    },
}


def get_expertise_preset(name: str) -> dict:
    """Return the preset dict for a given expertise type."""
    key = (name or "").strip().lower().replace("-", "_").replace(" ", "_")
    if key in EXPERTISE_PRESETS:
        return dict(EXPERTISE_PRESETS[key])
    # Fuzzy match
    for preset_key, preset in EXPERTISE_PRESETS.items():
        if preset_key in key or key in preset_key:
            return dict(preset)
        if preset["display_name"].lower() == key:
            return dict(preset)
    raise KeyError(
        f"Unknown expertise type '{name}'. "
        f"Available: {list(EXPERTISE_PRESETS.keys())}"
    )


def normalize_expertise_type(raw: str | None) -> str:
    """Normalize an expertise type string to a canonical preset key."""
    if not raw:
        return "troubleshooter"
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if key in EXPERTISE_PRESETS:
        return key
    for preset_key, preset in EXPERTISE_PRESETS.items():
        if preset_key in key or key in preset_key:
            return preset_key
        if preset["display_name"].lower() == key:
            return preset_key
    return "troubleshooter"


def list_expertise_types() -> list[dict]:
    """Return a summary list of all available expertise types."""
    return [
        {
            "name": p["name"],
            "display_name": p["display_name"],
            "description": p["description"],
            "knowledge_format": p["knowledge_format"],
        }
        for p in EXPERTISE_PRESETS.values()
    ]
