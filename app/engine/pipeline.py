from __future__ import annotations

import json
import uuid
from pathlib import Path

from .adapt import adapt_screenplay, build_adaptation_plan
from .continuity import build_continuity, contradictions_report
from .cultures import load_culture
from .extract import extract_project, merge_characters, retarget_character_id
from .models import CharacterRecord, CultureChoice, ProjectState
from .parse import parse_screenplay
from .pdfs import write_pdf
from .visuals import generate_visual_pack, retry_asset


class PipelineError(RuntimeError):
    pass


def new_project(source_text: str, culture: CultureChoice, filename: str = "pasted.txt") -> ProjectState:
    pack = load_culture(culture.culture_id)
    raw, problems = parse_screenplay(source_text)
    scenes, characters, locations, props, costumes = extract_project(raw, pack)
    continuity = build_continuity(scenes, costumes)
    plan = build_adaptation_plan(culture, pack, characters, scenes)
    return ProjectState(
        project_id=str(uuid.uuid4())[:8],
        source_filename=filename,
        source_text=source_text,
        culture=culture,
        extraction_problems=problems,
        scenes=scenes,
        characters=characters,
        locations=locations,
        props=props,
        costumes=costumes,
        continuity=continuity,
        adaptation_plan=plan,
        tool_calls=3,
    )


def merge_by_source(state: ProjectState, keep_source: str, drop_source: str) -> ProjectState:
    keep = next(c for c in state.characters if c.source_name.lower() == keep_source.lower() or c.character_id == keep_source)
    drop = next(c for c in state.characters if c.source_name.lower() == drop_source.lower() or c.character_id == drop_source)
    state.characters = merge_characters(state.characters, keep.source_name, drop.source_name)
    retarget_character_id(state.scenes, state.costumes, drop.character_id, keep.character_id)
    state.costumes = [c for c in state.costumes if c.character_id != drop.character_id]
    state.continuity = build_continuity(state.scenes, state.costumes)
    return state


def approve_extraction(state: ProjectState) -> ProjectState:
    for c in state.characters:
        c.approved = True
    for loc in state.locations:
        loc.approved = True
    for p in state.props:
        p.approved = True
    state.extraction_approved = True
    return state


def approve_plan_and_costumes(state: ProjectState) -> ProjectState:
    if state.adaptation_plan is None:
        raise PipelineError("No adaptation plan to approve.")
    state.adaptation_plan.approved = True
    for c in state.costumes:
        c.approved = True
    state.costumes_approved = True
    return state


def rewrite(state: ProjectState) -> ProjectState:
    pack = load_culture(state.culture.culture_id)
    text, gurmukhi, log = adapt_screenplay(state.source_text, state.scenes, state.characters, pack, state.culture)
    state.adapted_screenplay = text
    state.adapted_screenplay_gurmukhi = gurmukhi
    state.change_log = log
    state.model_calls += 1
    return state


def generate_visuals(state: ProjectState, out_dir: Path) -> ProjectState:
    if not state.extraction_approved or not state.costumes_approved or not (state.adaptation_plan and state.adaptation_plan.approved):
        raise PipelineError("Visual generation is blocked until extraction, cultural plan, and costumes are approved.")
    blocking = [w for s in state.scenes for w in s.continuity_warnings]
    if blocking:
        raise PipelineError("Continuity contradictions block generation: " + "; ".join(blocking))
    pack = load_culture(state.culture.culture_id)
    state.visuals = generate_visual_pack(out_dir, pack, state.culture, state.characters, state.costumes, state.scenes)
    state.tool_calls += len(state.visuals)
    return state


def retry_one_visual(state: ProjectState, asset_id: str, out_dir: Path) -> ProjectState:
    asset = next((v for v in state.visuals if v.asset_id == asset_id), None)
    if asset is None:
        raise PipelineError(f"Unknown asset {asset_id}")
    pack = load_culture(state.culture.culture_id)
    retry_asset(asset, pack, state.culture, state.characters, state.costumes, state.scenes, out_dir)
    return state


def inject_duplicate_alias(state: ProjectState) -> ProjectState:
    """Demo helper: source mention 'the elder son' extracted as a second identity."""
    adam = next(c for c in state.characters if c.character_id == "CHAR_ADAM")
    if any(c.character_id == "CHAR_ELDER_SON" for c in state.characters):
        return state
    state.characters.append(
        CharacterRecord(
            character_id="CHAR_ELDER_SON",
            source_name="Elder Son",
            adapted_name=adam.adapted_name,
            aliases=["Elder Son", "the elder son"],
            age=adam.age,
            role="duplicate of CHAR_ADAM — needs merge",
            dialect=adam.dialect,
            approved=False,
        )
    )
    return state


def inject_letter_contradiction(state: ProjectState) -> ProjectState:
    """Demo helper: letter vanishes in SC04 with no handoff — blocks visuals."""
    sc4 = next(s for s in state.scenes if s.scene_id == "SC04")
    sc4.action_lines = ["Adam enters without the jacket and sits immediately. The letter is gone."]
    sc4.dialogue = [{"speaker": "CHAR_ADAM", "source_name": "Adam", "text": "I lost it."}]
    sc4.props_present = [p for p in sc4.props_present if p != "PROP_LETTER"]
    state.continuity = build_continuity(state.scenes, state.costumes)
    return state


def apply_correction(state: ProjectState, kind: str, target_id: str, field: str, value: str) -> set[str]:
    """Patch an approved record. Returns canonical IDs whose visuals must be redrawn."""
    affected: set[str] = set()
    if kind == "character":
        char = next(c for c in state.characters if c.character_id == target_id or c.source_name.lower() == target_id.lower())
        if not hasattr(char, field):
            raise PipelineError(f"Unknown character field {field}")
        setattr(char, field, value)
        affected.add(char.character_id)
        for costume in state.costumes:
            if costume.character_id == char.character_id:
                affected.add(costume.costume_id)
        for scene in state.scenes:
            if char.character_id in scene.characters:
                affected.add(scene.scene_id)
    elif kind == "costume":
        costume = next(c for c in state.costumes if c.costume_id == target_id)
        if field == "colours":
            costume.colours = [part.strip() for part in value.split(",") if part.strip()]
        elif not hasattr(costume, field):
            raise PipelineError(f"Unknown costume field {field}")
        else:
            setattr(costume, field, value)
        affected.add(costume.costume_id)
        affected.add(costume.character_id)
        for scene in state.scenes:
            if costume.character_id in scene.characters:
                affected.add(scene.scene_id)
    elif kind == "plan":
        if not state.adaptation_plan:
            raise PipelineError("No plan to correct")
        decision = next(d for d in state.adaptation_plan.decisions if d.decision_id == target_id or d.topic == target_id)
        if field not in {"adapted", "reason"}:
            raise PipelineError("Plan corrections are limited to adapted text or reason")
        setattr(decision, field, value)
        if "bebe" in value.lower() or "maa" in value.lower() or field == "adapted":
            mother = next((c for c in state.characters if c.source_name.upper() == "MOTHER"), None)
            if mother and "maa" in value.lower():
                mother.adapted_name = value if "Kaur" in value else mother.adapted_name
                mother.aliases = list(dict.fromkeys(mother.aliases + ["Maa"]))
            affected.update(c.character_id for c in state.characters)
            affected.update(c.costume_id for c in state.costumes)
            affected.update(s.scene_id for s in state.scenes)
    else:
        raise PipelineError(f"Unknown correction kind {kind}")
    state.human_notes.append(f"corrected {kind} {target_id}.{field}={value}")
    return affected


def regenerate_affected(state: ProjectState, out_dir: Path, canonical_ids: set[str]) -> ProjectState:
    if not state.extraction_approved or not state.costumes_approved or not (state.adaptation_plan and state.adaptation_plan.approved):
        raise PipelineError("Visual generation is blocked until extraction, cultural plan, and costumes are approved.")
    blocking = [w for s in state.scenes for w in s.continuity_warnings]
    if blocking:
        raise PipelineError("Continuity contradictions block generation: " + "; ".join(blocking))
    pack = load_culture(state.culture.culture_id)
    refreshed = generate_visual_pack(
        out_dir, pack, state.culture, state.characters, state.costumes, state.scenes, only_canonical=canonical_ids
    )
    by_id = {v.canonical_id: v for v in refreshed}
    state.visuals = [by_id.get(v.canonical_id, v) for v in state.visuals]
    extra = [v for v in refreshed if all(v.canonical_id != x.canonical_id for x in state.visuals)]
    state.visuals.extend(extra)
    state.tool_calls += len(refreshed)
    return state


def export_pack(state: ProjectState, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    scene_path = out_dir / "scene_breakdown.json"
    scene_path.write_text(json.dumps([s.model_dump() for s in state.scenes], indent=2), encoding="utf-8")
    (out_dir / "characters.json").write_text(json.dumps([c.model_dump() for c in state.characters], indent=2), encoding="utf-8")
    (out_dir / "costumes.json").write_text(json.dumps([c.model_dump() for c in state.costumes], indent=2), encoding="utf-8")
    (out_dir / "adaptation_plan.json").write_text(
        json.dumps(state.adaptation_plan.model_dump() if state.adaptation_plan else {}, indent=2), encoding="utf-8"
    )
    (out_dir / "continuity.json").write_text(json.dumps([c.model_dump() for c in state.continuity], indent=2), encoding="utf-8")
    (out_dir / "visual_assets.json").write_text(json.dumps([v.model_dump() for v in state.visuals], indent=2), encoding="utf-8")
    (out_dir / "adapted_screenplay.txt").write_text(state.adapted_screenplay or "", encoding="utf-8")
    (out_dir / "change_log.json").write_text(json.dumps(state.change_log, indent=2), encoding="utf-8")

    contradictions = contradictions_report(state.scenes, state.continuity)
    report = _continuity_markdown(state, contradictions)
    (out_dir / "continuity_report.md").write_text(report, encoding="utf-8")
    write_pdf(out_dir / "adapted_screenplay.pdf", "Adapted Screenplay — Majhi", state.adapted_screenplay or "(not rewritten yet)")
    write_pdf(out_dir / "continuity_report.pdf", "Continuity Report", report)
    (out_dir / "project_state.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")
    return {
        "scene_breakdown": str(scene_path),
        "adapted_screenplay": str(out_dir / "adapted_screenplay.pdf"),
        "continuity_report": str(out_dir / "continuity_report.pdf"),
    }


def _continuity_markdown(state: ProjectState, contradictions: list[dict]) -> str:
    lines = [
        f"Project {state.project_id}",
        f"Culture: {state.culture.culture_id} / {state.culture.setting} / script={state.culture.script}",
        "",
        "## Canonical characters",
    ]
    for c in state.characters:
        lines.append(f"- {c.character_id}: {c.source_name} → {c.adapted_name} aliases={c.aliases}")
    lines.append("\n## Costumes (one variant unless story changes them)")
    for c in state.costumes:
        lines.append(f"- {c.costume_id} for {c.character_id} scenes={c.scenes}")
    lines.append("\n## Prop / knowledge / costume state")
    for st in state.continuity:
        lines.append(f"### {st.scene_id}")
        lines.append(f"wearing={st.wearing}")
        lines.append(f"carrying={st.carrying}")
        lines.append(f"knowledge={st.knowledge}")
        lines.append(f"emotion={st.emotion}")
        for n in st.notes:
            lines.append(f"- {n}")
    lines.append("\n## Contradictions")
    if not contradictions:
        lines.append("None. Letter custody, costumes, and knowledge track across scenes.")
    else:
        for row in contradictions:
            lines.append(f"- [{row['scene_id']}] {row['issue']}")
    lines.append("\n## Generation gates")
    lines.append(f"extraction_approved={state.extraction_approved}")
    lines.append(f"plan_approved={bool(state.adaptation_plan and state.adaptation_plan.approved)}")
    lines.append(f"costumes_approved={state.costumes_approved}")
    return "\n".join(lines)
