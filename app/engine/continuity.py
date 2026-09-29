from __future__ import annotations

from .models import ContinuityState, CostumeRecord, SceneRecord

LETTER = "PROP_LETTER"
JACKET = "PROP_JACKET"


def build_continuity(scenes: list[SceneRecord], costumes: list[CostumeRecord] | None = None) -> list[ContinuityState]:
    carrying: dict[str, set[str]] = {}
    knowledge: dict[str, set[str]] = {}
    wearing: dict[str, str] = {}
    states: list[ContinuityState] = []
    costume_for = {c.character_id: c.costume_id for c in (costumes or [])}

    for scene in sorted(scenes, key=lambda s: s.scene_number):
        warnings: list[str] = []
        notes: list[str] = []
        emotion: dict[str, str] = {}
        props_in: list[str] = []
        props_out: list[str] = []

        blob = " ".join(scene.action_lines + [d["text"] for d in scene.dialogue]).lower()
        adam = "CHAR_ADAM"
        mother = "CHAR_MOTHER"
        sister = "CHAR_SISTER"
        friend = "CHAR_FRIEND"

        for cid in scene.characters:
            costume_id = costume_for.get(cid) or next((x for x in scene.costume_ids if cid.replace("CHAR_", "") in x), "")
            prev = wearing.get(cid)
            if costume_id:
                wearing[cid] = costume_id
            if prev and costume_id and prev != costume_id:
                warnings.append(
                    f"{cid} costume changes from {prev} to {costume_id} in {scene.scene_id} without a stated story reason."
                )

        held = carrying.setdefault(adam, set())
        unexplained_loss = any(p in blob for p in ("i lost it", "lost the letter", "without the jacket", "letter is gone"))
        if unexplained_loss and LETTER in held:
            warnings.append(
                f"{scene.scene_id}: PROP_LETTER left Adam's custody without a tracked handoff. Affected previous scenes still list him carrying it."
            )

        if LETTER in scene.props_present or "letter" in blob or "envelope" in blob:
            held = carrying.setdefault(adam, set())
            if scene.scene_number == 1:
                held.add(LETTER)
                notes.append("Adam conceals the unopened letter in his jacket.")
                knowledge.setdefault(sister, set()).add("letter_exists")
                knowledge.setdefault(mother, set()).add("suspects_family_matter")
                emotion[adam] = "avoidance"
                emotion[mother] = "worry"
            elif scene.scene_number in (2, 3):
                if LETTER not in held:
                    warnings.append(
                        f"{scene.scene_id}: the letter is discussed or implied but Adam is not carrying PROP_LETTER from the previous scene."
                    )
                else:
                    notes.append("Letter remains in Adam's pocket; it does not change hands.")
                if scene.scene_number == 2:
                    knowledge.setdefault(friend, set()).add("uncle_wants_shop")
                    knowledge.setdefault(sister, set()).add("lie_about_course")
                    emotion[adam] = "cornered"
                    emotion[mother] = "insists_on_truth"
                else:
                    emotion[adam] = "public_pressure"
                    emotion[friend] = "pushes_him_home"
            elif scene.scene_number == 4:
                if LETTER not in held:
                    warnings.append(
                        f"{scene.scene_id}: Adam cannot place the letter on the table unless he still carries PROP_LETTER."
                    )
                if "places it" in blob or "places the envelope" in blob or "on the low table" in blob or "on the table" in blob:
                    held.discard(LETTER)
                    props_out.append(LETTER)
                    notes.append("Letter transfers from Adam's pocket to the baithak table — household custody.")
                    knowledge.setdefault(mother, set()).add("knows_shop_offer")
                    emotion[adam] = "admission"
                    emotion[mother] = "dignity_restored"
                    emotion[sister] = "solidarity"
                props_in.append(LETTER)

        scene.props_in = props_in
        scene.props_out = props_out
        scene.continuity_warnings = warnings
        scene.emotional_change = "; ".join(f"{k}: {v}" for k, v in emotion.items()) or scene.emotional_change

        states.append(
            ContinuityState(
                scene_id=scene.scene_id,
                wearing={cid: wearing.get(cid, "") for cid in scene.characters},
                carrying={cid: sorted(items) for cid, items in carrying.items() if items},
                knowledge={cid: sorted(items) for cid, items in knowledge.items() if items},
                injuries={},
                relationships={
                    adam: "son under izzat pressure",
                    mother: "household authority",
                    sister: "ally who refuses secrecy",
                    friend: "non-kin counsel",
                },
                emotion=emotion,
                notes=notes + warnings,
            )
        )
    return states


def contradictions_report(scenes: list[SceneRecord], states: list[ContinuityState]) -> list[dict]:
    rows = []
    for scene, state in zip(scenes, states):
        for warning in scene.continuity_warnings + [n for n in state.notes if "without" in n or "cannot" in n]:
            rows.append(
                {
                    "scene_id": scene.scene_id,
                    "issue": warning,
                    "affected_scenes": [scene.scene_id],
                    "blocks_generation": True,
                }
            )
    seen_chars = {}
    for scene in scenes:
        for cid in scene.characters:
            seen_chars.setdefault(cid, []).append(scene.scene_id)
    return rows
