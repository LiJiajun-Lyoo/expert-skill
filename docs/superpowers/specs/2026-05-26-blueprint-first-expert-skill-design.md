# Blueprint-First Expert Skill Creation Design

Date: 2026-05-26
Status: approved-for-spec-review
Branch: blueprint-first-expert-skill

## Problem

The current expert creation flow assumes the project already has an expert type preset, type-specific prompt templates, and often a matching example skill structure. This makes it cumbersome to create experts outside the built-in engineering and medical categories.

The product goal is broader: create an expert skill from any expert's explicit and tacit knowledge. The user should provide a description, materials, and interview answers; the system should infer how that expert thinks and works, then generate a usable Skill without requiring the user to preload templates or modify preset code.

## Goals

- Make expert type selection an inferred result, not a required starting input.
- Preserve existing built-in expert types as accelerators when the match is strong.
- Support unknown expert domains through a generic/custom generation path.
- Keep the current local workflow: generate prompt files, manually run a model, then parse the model output.
- Reuse the existing P2-P7 discovery pipeline instead of rewriting it.
- Generate the standard artifacts for both preset and custom experts: `SKILL.md`, `expertise.md`, `heuristics.json`, `knowledge_graph.md`, `meta.json`, and `manifest.json`.

## Non-Goals

- Do not add direct model API calls in this version.
- Do not auto-create and persist new global expert type templates for every unknown domain.
- Do not migrate existing generated skills.
- Do not remove or rewrite the current `standard` and `discovery` flows.
- Do not replace the existing prompt + parse-output operating model.

## Architecture

Add a new P2.5 "expert blueprint" stage between prior profile construction and latent variable discovery:

```text
User description + materials
  -> P2 pre_researcher
  -> discovery/expert_profile.json
  -> P2.5 blueprint_builder
  -> discovery/expert_blueprint_prompt.md
  -> discovery/expert_blueprint.json
  -> type match decision
      -> high confidence: use built-in preset
      -> low confidence or missing preset: use custom/generic generation
  -> P3 latent_variable_builder
  -> P4 triplet_generator
  -> P5 interview_session
  -> P6 interview_analyzer
  -> P7 skill_writer
```

`expertise_type` remains in `meta.json`, but it becomes an output of the blueprint decision unless the user explicitly forces it. Existing types continue to work. Unknown domains use `custom`, which means "blueprint-driven" rather than "untyped."

## Expert Blueprint Model

The new durable artifact is:

```text
skills/expert/{slug}/discovery/expert_blueprint.json
```

Recommended shape:

```json
{
  "identity_summary": {
    "name": "",
    "role": "",
    "domain": ""
  },
  "domain_summary": "",
  "primary_workflows": [],
  "decision_scenarios": [],
  "knowledge_shape": {
    "primary": "diagnostic | review | decision | operation | teaching | research | negotiation | hybrid | custom",
    "secondary": [],
    "reason": ""
  },
  "reasoning_framework": [],
  "tacit_knowledge_targets": [],
  "type_match": {
    "recommended_type": "troubleshooter | architect | reviewer | decision_maker | operator | clinical_care_manager | care_operation_specialist | medical_safety_reviewer | custom",
    "confidence": 0.0,
    "matched_signals": [],
    "rejected_types": []
  },
  "generation_strategy": {
    "mode": "preset | generic",
    "output_sections": [],
    "heuristics_shape": ""
  },
  "scope_boundaries": [],
  "evidence": []
}
```

Quality gates:

- `primary_workflows` must contain at least 2 items.
- `decision_scenarios` must contain at least 3 items.
- `tacit_knowledge_targets` must contain at least 5 items.
- `generation_strategy.output_sections` must not be empty.
- Type matching only uses a built-in preset when `type_match.confidence >= 0.75` and the recommended preset exists.
- If confidence is below threshold, or the preset is missing, the effective type becomes `custom` and `generation_strategy.mode` becomes `generic`.
- Key blueprint claims must have evidence from the profile, materials, or user description.

## Components

### `prompts/discovery/expert_blueprint.md`

New prompt template for producing an expert capability blueprint. It should ask the model to infer work patterns, decision situations, knowledge shape, tacit knowledge targets, scope boundaries, and type match confidence.

### `tools/blueprint_builder.py`

New P2.5 CLI tool.

Responsibilities:

- Read `expert_profile.json`.
- Optionally read additional user description or material summary files.
- Assemble `expert_blueprint_prompt.md`.
- Parse JSON or YAML model output.
- Validate blueprint schema and quality gates.
- Decide effective generation mode: built-in preset or `custom/generic`.
- Save `expert_blueprint.json` only when validation passes.
- Update `meta.json` discovery state to `blueprint_ready` when present.

### `tools/generic_skill_renderer.py`

New helper module for custom/generic generation.

Responsibilities:

- Convert `expert_blueprint.generation_strategy.output_sections` into an `expertise.md` structure.
- Convert workflows, decision scenarios, reasoning framework, tacit targets, and boundaries into `heuristics.json`.
- Render a useful `knowledge_graph.md` from blueprint concepts and discovery analysis.
- Avoid dependence on `prompts/expertise/{type}/...` templates.

### `tools/expertise_presets.py`

Add a first-class `custom` preset for compatibility with the existing writer, schema, and manifest code. The preset should identify the expert as blueprint-driven and use generic labels such as capability blueprint, reasoning framework, tacit variables, and operating boundaries.

### Existing Discovery Tools

`latent_variable_builder.py` should prefer `expert_blueprint.tacit_knowledge_targets` as seeds when available, then fall back to the current profile-only path.

`triplet_generator.py` should prefer `expert_blueprint.decision_scenarios` and `primary_workflows` for realistic scenarios, then fall back to the current profile data.

`skill_writer.py` should accept `--blueprint`. When the effective type is `custom` or `generation_strategy.mode == "generic"`, it should use generic rendering for knowledge artifacts while preserving the current output filenames and manifest shape.

## Data Flow

1. P2 writes `expert_profile.json`.
2. P2.5 writes `expert_blueprint_prompt.md`.
3. The user runs that prompt through a model and saves the output.
4. P2.5 parses the model output, validates it, resolves effective type, and writes `expert_blueprint.json`.
5. P3 consumes profile plus blueprint seeds and writes `latent_variables.json`.
6. P4 consumes profile plus blueprint scenarios and writes `triplet_groups.json` and `interview_script.md`.
7. P5 and P6 continue as today.
8. P7 writes final skill artifacts using either the matched preset or the generic renderer.

## Error Handling

- Missing `expert_blueprint.json`: existing tools continue with old behavior.
- Invalid blueprint output: do not save `expert_blueprint.json`; print all schema and quality gate errors.
- Low-confidence preset match: override effective type to `custom` and record `type_match_overridden: true`.
- Missing built-in preset: downgrade to `custom/generic` instead of failing creation.
- Empty generic output sections: block final generic rendering and require blueprint regeneration or manual correction.
- User-forced `--expertise-type`: honor the forced type, but record `type_forced_by_user: true` in metadata.

## Metadata

Extend discovery status with `blueprint_ready`.

Recommended metadata additions:

```json
{
  "discovery": {
    "enabled": true,
    "status": "blueprint_ready",
    "blueprint": {
      "path": "discovery/expert_blueprint.json",
      "effective_type": "custom",
      "generation_mode": "generic",
      "type_match_confidence": 0.62,
      "type_match_overridden": true,
      "type_forced_by_user": false
    }
  }
}
```

Existing skills without this block remain valid.

## Compatibility

- Existing built-in expert types keep their current presets and prompts.
- Existing `standard` and `discovery` commands continue to work.
- Existing generated skills do not need migration.
- Existing tests and fixtures should continue passing.
- The new blueprint stage is optional for old flows and expected for the new "any expert" creation flow.

## Testing

Add unit tests for:

- Blueprint schema validation.
- Blueprint quality gates.
- Type match threshold behavior.
- Built-in preset selection when confidence is high.
- Automatic `custom/generic` downgrade when confidence is low or preset is missing.
- `blueprint_builder.py` dry-run behavior.
- Prompt assembly without leftover placeholders.
- Parse-output save path.
- Meta update to `blueprint_ready`.

Add integration smoke coverage for an unknown expert domain, such as a supply-chain negotiation expert or investment committee expert:

- No type-specific prompt folder exists.
- No new hard-coded preset beyond `custom` is required.
- Blueprint resolves to `custom/generic`.
- P3 and P4 consume blueprint seeds.
- P7 produces `SKILL.md`, `expertise.md`, `heuristics.json`, `knowledge_graph.md`, `meta.json`, and `manifest.json`.
- Existing `mock_expert` P2-P7 smoke tests still pass.

Acceptance command:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools uvx pytest -q
```

## Branching Plan

This spec lives on the unified feature branch:

```text
blueprint-first-expert-skill
```

The same branch should contain the design document, planning document, and implementation changes. After spec review approval, add the planning document and code changes in this same worktree. Keep the phases reviewable through separate commits rather than separate branches.
