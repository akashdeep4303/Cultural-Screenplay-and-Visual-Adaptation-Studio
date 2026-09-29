from __future__ import annotations

import re

from .models import CharacterRecord, CostumeRecord, ProductionElement, SceneRecord
from .parse import RawScene

PROP_WORDS = {
    "letter": ["letter", "envelope"],
    "jacket": ["jacket", "pocket"],
    "kettle": ["kettle"],
    "cups": ["cup", "cups"],
    "phone": ["phone"],
    "lamp": ["lamp"],
}

ROLE_HINTS = {
    "Mother": "mother / household centre",
    "Adam": "elder son / reluctant heir",
    "Sister": "younger sister / witness",
    "Friend": "childhood friend / pressure valve",
    "Uncle": "maternal uncle / off-stage catalyst",
}


def extract_project(raw_scenes: list[RawScene], culture: dict) -> tuple[list[SceneRecord], list[CharacterRecord], list[ProductionElement], list[ProductionElement], list[CostumeRecord]]:
    characters: dict[str, CharacterRecord] = {}
    locations: dict[str, ProductionElement] = {}
    props: dict[str, ProductionElement] = {}
    scenes: list[SceneRecord] = []

    for raw in raw_scenes:
        loc_key = _slug(raw.location)
        loc_id = f"LOC_{loc_key}"
        if loc_id not in locations:
            locations[loc_id] = ProductionElement(
                element_id=loc_id,
                kind="location",
                source_name=raw.location,
                first_scene=f"SC{raw.number:02d}",
                scenes=[f"SC{raw.number:02d}"],
            )
        else:
            locations[loc_id].scenes.append(f"SC{raw.number:02d}")

        speakers = []
        dialogue = []
        action = []
        for beat in raw.beats:
            if beat.kind == "dialogue":
                cid = _character_id(beat.speaker)
                speakers.append(cid)
                if cid not in characters:
                    characters[cid] = CharacterRecord(
                        character_id=cid,
                        source_name=beat.speaker,
                        aliases=[beat.speaker],
                        role=ROLE_HINTS.get(beat.speaker, "supporting"),
                        entrance_scene=f"SC{raw.number:02d}",
                        personality=_personality(beat.speaker),
                    )
                else:
                    if beat.speaker not in characters[cid].aliases:
                        characters[cid].aliases.append(beat.speaker)
                    characters[cid].exit_scene = f"SC{raw.number:02d}"
                dialogue.append({"speaker": cid, "source_name": beat.speaker, "text": beat.text})
            else:
                action.append(beat.text)
                _maybe_alias_from_action(beat.text, characters)
                for mention in _mentions_from_action(beat.text):
                    cid = _character_id(mention)
                    speakers.append(cid)
                    if cid not in characters:
                        characters[cid] = CharacterRecord(
                            character_id=cid,
                            source_name=mention,
                            aliases=[mention],
                            role=ROLE_HINTS.get(mention, "off-stage relation"),
                            entrance_scene=f"SC{raw.number:02d}",
                            personality=_personality(mention),
                        )

        present_props = _props_in_text(" ".join(action + [d["text"] for d in dialogue]))
        scene_id = f"SC{raw.number:02d}"
        for prop_key in present_props:
            pid = f"PROP_{prop_key.upper()}"
            if pid not in props:
                props[pid] = ProductionElement(
                    element_id=pid,
                    kind="prop",
                    source_name=prop_key,
                    first_scene=scene_id,
                    scenes=[scene_id],
                    description=f"Recurring prop: {prop_key}",
                )
            elif scene_id not in props[pid].scenes:
                props[pid].scenes.append(scene_id)

        unique_chars = list(dict.fromkeys(speakers))
        scenes.append(
            SceneRecord(
                scene_id=scene_id,
                scene_number=raw.number,
                int_ext=raw.int_ext,
                location=raw.location,
                location_id=loc_id,
                time=raw.time,
                day_or_date="Day 1" if raw.number < 4 else "Day 1 evening",
                weather=_weather(raw.time, raw.int_ext),
                mood=_mood(raw.number),
                summary=_summary(action, dialogue),
                dramatic_purpose=_purpose(raw.number),
                characters=unique_chars,
                props_present=[f"PROP_{p.upper()}" for p in present_props],
                source_heading=raw.heading,
                action_lines=action,
                dialogue=dialogue,
            )
        )

    costumes = []
    for char in characters.values():
        costume_id = f"COST_{char.character_id.replace('CHAR_', '')}_01"
        pack = culture.get("costumes", {}).get(char.source_name.upper(), {})
        if not pack:
            pack = culture.get("costumes", {}).get(char.source_name, {})
        costumes.append(
            CostumeRecord(
                costume_id=costume_id,
                character_id=char.character_id,
                label=f"{char.source_name} — day look",
                garments=pack.get("garments", "Source-neutral clothing pending cultural plan"),
                fabrics="Cotton / khaddar unless urban setting selected",
                colours=pack.get("colours", []),
                footwear=pack.get("footwear", ""),
                jewellery=pack.get("jewellery", ""),
                headwear=pack.get("headwear", pack.get("grooming", "")),
                grooming=pack.get("grooming", ""),
                scenes=[s.scene_id for s in scenes if char.character_id in s.characters],
            )
        )

    for scene in scenes:
        scene.costume_ids = [f"COST_{cid.replace('CHAR_', '')}_01" for cid in scene.characters]

    _apply_culture_character_fields(characters, culture)
    return scenes, list(characters.values()), list(locations.values()), list(props.values()), costumes


def merge_characters(characters: list[CharacterRecord], source_a: str, source_b: str) -> list[CharacterRecord]:
    keep = _character_id(source_a)
    drop = _character_id(source_b)
    primary = next((c for c in characters if c.character_id == keep), None)
    secondary = next((c for c in characters if c.character_id == drop), None)
    if not primary or not secondary:
        return characters
    for alias in secondary.aliases + [secondary.source_name]:
        if alias not in primary.aliases:
            primary.aliases.append(alias)
    return [c for c in characters if c.character_id != drop]


def retarget_character_id(scenes: list[SceneRecord], costumes: list[CostumeRecord], old_id: str, new_id: str) -> None:
    for scene in scenes:
        scene.characters = [new_id if c == old_id else c for c in scene.characters]
        for line in scene.dialogue:
            if line.get("speaker") == old_id:
                line["speaker"] = new_id
    for costume in costumes:
        if costume.character_id == old_id:
            costume.character_id = new_id


def _apply_culture_character_fields(characters: dict[str, CharacterRecord], culture: dict) -> None:
    names = culture.get("names", {})
    dialect = culture.get("dialect", "")
    for char in characters.values():
        key = char.source_name.upper()
        row = names.get(key) or names.get(char.source_name)
        if not row:
            continue
        char.adapted_name = row["adapted_name"]
        char.aliases = list(dict.fromkeys(char.aliases + row.get("aliases", [])))
        char.age = str(row.get("age", ""))
        char.role = row.get("family_role", char.role)
        char.dialect = dialect
        char.physical_description = f"{row.get('work', '')}; {row.get('family_role', '')}"
        char.grooming = culture.get("costumes", {}).get(key, {}).get("grooming", "")
        char.relationships = _relationships(char.source_name)


def _relationships(name: str) -> list[str]:
    table = {
        "Adam": ["son of Mother", "elder brother of Sister", "friend of Friend", "nephew of Uncle"],
        "Mother": ["mother of Adam and Sister", "sister of Uncle"],
        "Sister": ["daughter of Mother", "younger sister of Adam"],
        "Friend": ["childhood friend of Adam"],
        "Uncle": ["maternal uncle of Adam and Sister", "brother of Mother"],
    }
    return table.get(name, [])


def _personality(name: str) -> str:
    table = {
        "Adam": "Avoidant under family pressure; loyal; slow to speak",
        "Mother": "Direct, dignity-first, unwilling to be last to know",
        "Sister": "Clear-eyed, protective, refuses theatrical secrecy",
        "Friend": "Teasing, locally grounded, pushes Adam toward the house not the street",
        "Uncle": "Off-stage authority through the letter and the shop",
    }
    return table.get(name, "Supporting")


def _maybe_alias_from_action(text: str, characters: dict[str, CharacterRecord]) -> None:
    lowered = text.lower()
    mapping = {
        "his uncle": "Uncle",
        "her brother": "Uncle",
        "my uncle": "Uncle",
        "elder son": "Adam",
        "the mother": "Mother",
        "his mother": "Mother",
        "her son": "Adam",
        "her daughter": "Sister",
    }
    for phrase, canon in mapping.items():
        if phrase in lowered:
            cid = _character_id(canon)
            if cid in characters and canon not in characters[cid].aliases:
                characters[cid].aliases.append(phrase)


def _mentions_from_action(text: str) -> list[str]:
    found = []
    if re.search(r"\buncle\b", text, re.I):
        found.append("Uncle")
    return found


def _props_in_text(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for key, words in PROP_WORDS.items():
        if any(w in lower for w in words):
            found.append(key)
    return found


def _summary(action: list[str], dialogue: list[dict]) -> str:
    if action:
        return action[0][:180]
    if dialogue:
        return dialogue[0]["text"][:180]
    return "Scene extracted with limited action text."


def _purpose(number: int) -> str:
    return {
        1: "Establish concealment of the letter and household pressure",
        2: "Force the lie into the kitchen, the moral centre of the house",
        3: "Test the decision in public space without allowing a public refusal",
        4: "Return the letter to the family table and restore truth-telling",
    }.get(number, "Advance the family conflict")


def _mood(number: int) -> str:
    return {1: "uneasy dawn", 2: "tight domestic confrontation", 3: "heat and avoidance", 4: "quiet reckoning"}.get(number, "tense")


def _weather(time: str, int_ext: str) -> str:
    if int_ext == "EXT" and "morning" in time.lower():
        return "dew, pale light"
    if int_ext == "EXT":
        return "hot, dusty"
    return "indoor, still air"


def _character_id(name: str) -> str:
    return "CHAR_" + re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")


def _slug(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", text.upper()).strip("_")
