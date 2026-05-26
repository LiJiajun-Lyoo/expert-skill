#!/usr/bin/env python3
"""
Blueprint builder tool for the P2.5 discovery phase.

Reads expert_profile.json, assembles the blueprint prompt, and optionally
parses model output to produce expert_blueprint.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from discovery_schema import resolve_blueprint_type_match, validate_expert_blueprint
from expertise_presets import list_expertise_types

PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent / "prompts" / "discovery" / "expert_blueprint.md"


def read_expert_profile(base_dir: str, slug: str) -> dict:
    """Read the P2 expert profile for a skill slug."""
    path = Path(base_dir) / slug / "discovery" / "expert_profile.json"
    if not path.exists():
        raise FileNotFoundError(f"找不到 {path}；请先完成 P2 生成 expert_profile.json")
    return json.loads(path.read_text(encoding="utf-8"))


def read_optional_text(paths: list[Path]) -> str:
    """Read optional UTF-8 text files and join them with blank lines."""
    return "\n\n".join(path.read_text(encoding="utf-8") for path in paths)


def assemble_prompt(
    template: str,
    name: str,
    expert_profile_json: str,
    user_description: str = "",
    material_summary: str = "",
) -> str:
    """Replace blueprint prompt placeholders with concrete values."""
    replacements = {
        "{name}": name or "（未填写）",
        "{expert_profile_json}": expert_profile_json or "（未提供）",
        "{user_description}": user_description or "（未填写）",
        "{material_summary}": material_summary or "（未提供）",
    }
    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result


def _unwrap_blueprint(data: object) -> dict:
    if isinstance(data, dict):
        blueprint = data.get("expert_blueprint", data)
        if isinstance(blueprint, dict):
            return blueprint
    raise ValueError(f"输出必须是 JSON/YAML object 或包含 expert_blueprint 的 object，实际为 {type(data)}")


def _parse_output_file(output_path: Path) -> dict:
    """Parse a model output file as JSON first, then YAML if available."""
    text = output_path.read_text(encoding="utf-8")

    try:
        return _unwrap_blueprint(json.loads(text))
    except json.JSONDecodeError:
        pass
    except ValueError as exc:
        print(f"错误：无法解析输出文件（{exc}）", file=sys.stderr)
        sys.exit(1)

    try:
        import yaml  # type: ignore

        return _unwrap_blueprint(yaml.safe_load(text))
    except ImportError:
        print(
            "错误：输入文件不是有效 JSON，且 PyYAML 未安装。\n"
            "请安装 PyYAML（pip install pyyaml）以支持 YAML 输入，"
            "或将 AI 输出保存为 JSON 格式后重试。",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        print(f"错误：无法解析输出文件（{exc}）", file=sys.stderr)
        sys.exit(1)


def _resolve_and_apply_type_match(blueprint: dict) -> dict:
    """Resolve preset/custom type matching and write the decision into blueprint."""
    available_types = [item["name"] for item in list_expertise_types()]
    resolved = resolve_blueprint_type_match(blueprint, available_types)
    type_match = blueprint.setdefault("type_match", {})
    type_match["effective_type"] = resolved["effective_type"]
    type_match["type_match_overridden"] = resolved["type_match_overridden"]
    blueprint.setdefault("generation_strategy", {})["mode"] = resolved["generation_mode"]
    return blueprint


def _update_meta_json(meta_path: Path, resolved: dict) -> None:
    """Update discovery status and blueprint summary in an existing meta.json."""
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    discovery = meta.setdefault("discovery", {})
    discovery["enabled"] = True
    discovery["status"] = "blueprint_ready"
    discovery["blueprint"] = {
        "path": "discovery/expert_blueprint.json",
        "effective_type": resolved["effective_type"],
        "generation_mode": resolved["generation_mode"],
        "type_match_confidence": resolved["type_match_confidence"],
        "type_match_overridden": resolved["type_match_overridden"],
        "type_forced_by_user": False,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _profile_name(profile: dict) -> str:
    identity = profile.get("identity", {})
    if isinstance(identity, dict):
        return str(identity.get("name") or "")
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P2.5 专家能力蓝图工具：组装 prompt 并可选解析 AI 输出")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--base-dir", default="./skills/expert", dest="base_dir")
    parser.add_argument("--user-description", default="", dest="user_description")
    parser.add_argument("--material-summary", nargs="+", metavar="FILE", default=[], dest="material_summary")
    parser.add_argument("--parse-output", default="", metavar="FILE", dest="parse_output")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    args = parser.parse_args(argv)

    if args.dry_run and args.parse_output:
        print("错误：--dry-run 与 --parse-output 不能同时使用", file=sys.stderr)
        return 1

    if not PROMPT_TEMPLATE_PATH.exists():
        print(f"错误：找不到 prompt 模板文件 {PROMPT_TEMPLATE_PATH}", file=sys.stderr)
        return 1

    material_paths = [Path(path) for path in args.material_summary]
    for path in material_paths:
        if not path.exists():
            print(f"错误：材料摘要文件不存在：{path}", file=sys.stderr)
            return 1

    try:
        profile = read_expert_profile(args.base_dir, args.slug)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    expert_profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
    prompt = assemble_prompt(
        template=template,
        name=_profile_name(profile),
        expert_profile_json=expert_profile_json,
        user_description=args.user_description,
        material_summary=read_optional_text(material_paths),
    )

    if args.dry_run:
        print(prompt)
        return 0

    discovery_dir = Path(args.base_dir) / args.slug / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = discovery_dir / "expert_blueprint_prompt.md"
    prompt_file.write_text(prompt, encoding="utf-8")
    print(f"[OK] prompt written: {prompt_file}")

    if args.parse_output:
        output_path = Path(args.parse_output)
        if not output_path.exists():
            print(f"错误：输出文件不存在：{output_path}", file=sys.stderr)
            return 1

        blueprint = _parse_output_file(output_path)
        schema_errors = validate_expert_blueprint(blueprint)
        if schema_errors:
            print("错误：schema 验证不通过，expert_blueprint.json 不保存：", file=sys.stderr)
            for error in schema_errors:
                print(f"  - {error}", file=sys.stderr)
            return 1

        resolved = resolve_blueprint_type_match(
            blueprint,
            [item["name"] for item in list_expertise_types()],
        )
        blueprint = _resolve_and_apply_type_match(blueprint)
        blueprint_path = discovery_dir / "expert_blueprint.json"
        blueprint_path.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] expert_blueprint.json saved: {blueprint_path}")

        meta_path = Path(args.base_dir) / args.slug / "meta.json"
        if meta_path.exists():
            _update_meta_json(meta_path, resolved)
            print("[OK] meta.json updated (discovery.enabled=true, discovery.status=blueprint_ready)")
        else:
            print("Note: meta.json not found, discovery status not written")

    return 0


if __name__ == "__main__":
    sys.exit(main())
