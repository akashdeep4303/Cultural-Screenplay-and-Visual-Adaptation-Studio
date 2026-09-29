from pathlib import Path

from app.engine.continuity import build_continuity
from app.engine.cultures import load_culture
from app.engine.extract import extract_project
from app.engine.models import CultureChoice, SceneRecord
from app.engine.parse import parse_screenplay
from app.engine.pipeline import (
    PipelineError,
    apply_correction,
    approve_extraction,
    approve_plan_and_costumes,
    generate_visuals,
    inject_letter_contradiction,
    merge_by_source,
    new_project,
    regenerate_affected,
    retry_one_visual,
    rewrite,
)


SAMPLE = Path("app/data/sample_screenplay.txt").read_text(encoding="utf-8")


def _choice(cid="majhi", setting="rural"):
    pack = load_culture(cid)
    return CultureChoice(
        culture_id=cid,
        dialect=pack["dialect"],
        region=pack["region"],
        setting=setting,
        script="roman",
    )


def test_extracts_four_scenes_and_canonical_characters():
    state = new_project(SAMPLE, _choice())
    assert [s.scene_id for s in state.scenes] == ["SC01", "SC02", "SC03", "SC04"]
    ids = {c.character_id for c in state.characters}
    assert "CHAR_ADAM" in ids
    assert "CHAR_MOTHER" in ids
    assert "CHAR_UNCLE" in ids
    adam = next(c for c in state.characters if c.character_id == "CHAR_ADAM")
    assert any("uncle" in a.lower() for a in adam.aliases) or "Uncle" in [c.source_name for c in state.characters]


def test_alias_merge_removes_duplicate_identity():
    state = new_project(SAMPLE, _choice())
    state.characters.append(
        state.characters[0].model_copy(
            update={"character_id": "CHAR_ELDER_SON", "source_name": "Elder Son", "aliases": ["Elder Son"]}
        )
    )
    merge_by_source(state, "Adam", "Elder Son")
    ids = [c.character_id for c in state.characters]
    assert "CHAR_ELDER_SON" not in ids
    adam = next(c for c in state.characters if c.character_id == "CHAR_ADAM")
    assert "Elder Son" in adam.aliases


def test_letter_continuity_tracks_across_scenes():
    state = new_project(SAMPLE, _choice())
    sc4 = next(s for s in state.continuity if s.scene_id == "SC04")
    # After scene 4 the letter has left Adam's pocket.
    carrying = sc4.carrying.get("CHAR_ADAM", [])
    assert "PROP_LETTER" not in carrying
    sc2 = next(s for s in state.continuity if s.scene_id == "SC02")
    assert "PROP_LETTER" in sc2.carrying.get("CHAR_ADAM", [])


def test_missing_letter_is_a_blocking_contradiction():
    raw, _ = parse_screenplay(SAMPLE)
    pack = load_culture("majhi")
    scenes, chars, locs, props, costumes = extract_project(raw, pack)
    # Break continuity: scene 4 no longer mentions the letter and Adam is empty-handed.
    sc4 = next(s for s in scenes if s.scene_id == "SC04")
    sc4.action_lines = ["Adam enters without the jacket and sits immediately."]
    sc4.dialogue = [{"speaker": "CHAR_ADAM", "source_name": "Adam", "text": "I lost it."}]
    sc4.props_present = []
    states = build_continuity(scenes, costumes)
    warnings = [w for s in scenes for w in s.continuity_warnings]
    assert any("PROP_LETTER" in w or "letter" in w.lower() for w in warnings)
    assert states[-1].notes


def test_visuals_blocked_without_approval(tmp_path):
    state = new_project(SAMPLE, _choice())
    try:
        generate_visuals(state, tmp_path)
        assert False, "should have blocked"
    except PipelineError as exc:
        assert "approved" in str(exc).lower()


def test_end_to_end_majhi_not_malwai(tmp_path):
    state = new_project(SAMPLE, _choice("majhi"))
    approve_extraction(state)
    approve_plan_and_costumes(state)
    rewrite(state)
    generate_visuals(state, tmp_path)
    assert "Bebe" in state.adapted_screenplay
    assert "Harbans Kaur" not in state.adapted_screenplay
    assert "Balwinder" not in state.adapted_screenplay
    assert any(v.kind == "character" for v in state.visuals)
    assert any(v.kind == "scene" for v in state.visuals)
    # one costume per on-screen character, reused
    onscreen = [c.character_id for c in state.characters if c.source_name != "Uncle"]
    cost_for = [c for c in state.costumes if c.character_id in onscreen]
    assert len(cost_for) == len(set(c.character_id for c in cost_for))


def test_culture_memory_does_not_leak():
    majhi = new_project(SAMPLE, _choice("majhi"))
    malwai = new_project(SAMPLE, _choice("malwai"))
    rewrite(majhi)
    rewrite(malwai)
    assert "Bebe" in majhi.adapted_screenplay
    assert "Bebe" not in malwai.adapted_screenplay
    assert "Maa" in malwai.adapted_screenplay or "Harbans" in "".join(c.adapted_name for c in malwai.characters)
    assert majhi.project_id != malwai.project_id


def test_retry_single_asset(tmp_path):
    state = new_project(SAMPLE, _choice())
    approve_extraction(state)
    approve_plan_and_costumes(state)
    rewrite(state)
    generate_visuals(state, tmp_path)
    asset_id = state.visuals[0].asset_id
    retry_one_visual(state, asset_id, tmp_path)
    assert state.visuals[0].status == "ok"


def test_letter_contradiction_blocks_visuals(tmp_path):
    state = new_project(SAMPLE, _choice())
    approve_extraction(state)
    approve_plan_and_costumes(state)
    inject_letter_contradiction(state)
    try:
        generate_visuals(state, tmp_path)
        assert False, "should have blocked"
    except PipelineError as exc:
        assert "letter" in str(exc).lower() or "contradiction" in str(exc).lower()


def test_correction_regenerates_only_affected(tmp_path):
    state = new_project(SAMPLE, _choice())
    approve_extraction(state)
    approve_plan_and_costumes(state)
    rewrite(state)
    generate_visuals(state, tmp_path)
    before = {v.canonical_id: Path(v.path).read_text(encoding="utf-8") for v in state.visuals}
    affected = apply_correction(state, "costume", "COST_ADAM_01", "colours", "mustard, navy, dust tan")
    regenerate_affected(state, tmp_path, affected)
    after = {v.canonical_id: Path(v.path).read_text(encoding="utf-8") for v in state.visuals}
    assert "CHAR_ADAM" in affected
    assert "COST_ADAM_01" in affected
    assert after["CHAR_ADAM"] != before["CHAR_ADAM"]
    assert after["COST_SISTER_01"] == before["COST_SISTER_01"]
    adam = tmp_path / "character_bible" / "CHAR_ADAM.svg"
    assert "CHAR_ADAM" in adam.read_text(encoding="utf-8")


def test_parser_reports_missing_headings():
    scenes, problems = parse_screenplay("ADAM\nHello there.\n")
    assert scenes == []
    assert problems
