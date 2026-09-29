from __future__ import annotations

import hashlib
from pathlib import Path

from .models import CharacterRecord, CostumeRecord, CultureChoice, SceneRecord, VisualAsset

RENDERER = "svg-renderer-v3"


def generate_visual_pack(
    out_dir: Path,
    culture: dict,
    culture_choice: CultureChoice,
    characters: list[CharacterRecord],
    costumes: list[CostumeRecord],
    scenes: list[SceneRecord],
    only_canonical: set[str] | None = None,
    only_kind: str | None = None,
) -> list[VisualAsset]:
    palette = culture["palette"]
    assets: list[VisualAsset] = []
    char_dir = out_dir / "character_bible"
    cost_dir = out_dir / "costume_bible"
    scene_dir = out_dir / "scene_keyframes"
    for d in (char_dir, cost_dir, scene_dir):
        d.mkdir(parents=True, exist_ok=True)

    char_by_id = {c.character_id: c for c in characters}
    costume_by_char = {c.character_id: c for c in costumes}
    important = [c for c in characters if c.source_name.upper() != "UNCLE"]

    for char in important:
        if only_kind and only_kind != "character":
            continue
        if only_canonical and char.character_id not in only_canonical:
            continue
        costume = costume_by_char.get(char.character_id)
        seed = _seed(char.character_id + culture_choice.culture_id)
        path = char_dir / f"{char.character_id}.svg"
        path.write_text(_character_svg(char, costume, palette, seed, culture_choice), encoding="utf-8")
        assets.append(
            VisualAsset(
                asset_id=f"VIS_{char.character_id}",
                kind="character",
                canonical_id=char.character_id,
                title=char.adapted_name or char.source_name,
                path=str(path),
                prompt=_character_prompt(char, costume, culture, culture_choice),
                model=RENDERER,
                seed=seed,
                status="ok",
            )
        )

    for costume in costumes:
        char = char_by_id.get(costume.character_id)
        if not char or char.source_name.upper() == "UNCLE":
            continue
        if only_kind and only_kind != "costume":
            continue
        if only_canonical and costume.costume_id not in only_canonical and char.character_id not in only_canonical:
            continue
        seed = _seed(costume.costume_id + culture_choice.culture_id)
        path = cost_dir / f"{costume.costume_id}.svg"
        path.write_text(_costume_svg(char, costume, palette, culture_choice), encoding="utf-8")
        assets.append(
            VisualAsset(
                asset_id=f"VIS_{costume.costume_id}",
                kind="costume",
                canonical_id=costume.costume_id,
                title=costume.label,
                path=str(path),
                prompt=_costume_prompt(char, costume, culture_choice),
                model=RENDERER,
                seed=seed,
                status="ok",
            )
        )

    for scene in scenes:
        if only_kind and only_kind != "scene":
            continue
        if only_canonical and scene.scene_id not in only_canonical:
            continue
        seed = _seed(scene.scene_id + culture_choice.culture_id + culture_choice.setting)
        path = scene_dir / f"{scene.scene_id}.svg"
        path.write_text(_scene_svg(scene, characters, costumes, palette, culture_choice), encoding="utf-8")
        assets.append(
            VisualAsset(
                asset_id=f"VIS_{scene.scene_id}",
                kind="scene",
                canonical_id=scene.scene_id,
                title=f"{scene.scene_id} {scene.location}",
                path=str(path),
                prompt=_scene_prompt(scene, characters, costumes, culture, culture_choice),
                model=RENDERER,
                seed=seed,
                status="ok",
            )
        )
    return assets


def retry_asset(
    asset: VisualAsset,
    culture: dict,
    culture_choice: CultureChoice,
    characters: list[CharacterRecord],
    costumes: list[CostumeRecord],
    scenes: list[SceneRecord],
    out_dir: Path,
) -> VisualAsset:
    generated = generate_visual_pack(
        out_dir,
        culture,
        culture_choice,
        characters,
        costumes,
        scenes,
        only_canonical={asset.canonical_id},
        only_kind=asset.kind,
    )
    if generated:
        fresh = generated[0]
        asset.path = fresh.path
        asset.seed = fresh.seed
        asset.prompt = fresh.prompt
        asset.model = RENDERER
    asset.status = "ok"
    asset.error = ""
    return asset


def _seed(key: str) -> str:
    return hashlib.sha1(key.encode()).hexdigest()[:10]


def _character_prompt(char, costume, culture, choice: CultureChoice) -> str:
    c = costume
    return (
        f"Photoreal production still, full-body character bible of {char.adapted_name}, "
        f"Majhi Punjabi {choice.setting} {choice.region}, age {char.age}, "
        f"{c.garments if c else ''}, {c.grooming if c else ''}, kara visible, "
        f"natural skin texture, documentary lighting, dusty courtyard backdrop, "
        f"culturally specific not generic Indian costume, consistent face and body. "
        f"Culture id={choice.culture_id} only."
    )


def _costume_prompt(char, costume, choice: CultureChoice) -> str:
    return (
        f"Costume bible plate for {costume.costume_id} worn by {char.adapted_name}: {costume.garments}. "
        f"Show garments, fabrics, colours {', '.join(costume.colours)}, footwear {costume.footwear}, "
        f"jewellery {costume.jewellery}. One unique variant reused in scenes {', '.join(costume.scenes)}. "
        f"{choice.culture_id} {choice.setting} only."
    )


def _scene_prompt(scene, characters, costumes, culture, choice: CultureChoice) -> str:
    names = [c.adapted_name for c in characters if c.character_id in scene.characters]
    loc = culture.get("locations", {})
    meta = {}
    for k, v in loc.items():
        if k in scene.location.upper():
            meta = v
            break
    arch = meta.get("architecture") if choice.setting == "rural" else meta.get("urban_variant")
    return (
        f"Cinematic keyframe {scene.scene_id}: {scene.int_ext} {arch}. Time {scene.time}, weather {scene.weather}. "
        f"Characters {names} in approved costumes {scene.costume_ids}. Props {scene.props_present}. "
        f"Mood {scene.mood}. Blocking tells Majha even if dialogue is hidden. "
        f"Do not mix Malwai or generic Rajasthani/Punjabi-stock look."
    )


def _look(char: CharacterRecord, costume: CostumeRecord | None, palette: dict) -> dict:
    key = char.source_name.upper()
    colors = (costume.colours if costume else []) or ["off-white"]
    primary = _colour(colors[0], palette)
    secondary = _colour(colors[1] if len(colors) > 1 else "navy", palette)
    tertiary = _colour(colors[2] if len(colors) > 2 else "dust tan", palette)
    skins = {
        "ADAM": ("#c48a5a", "#e8c39a", "#8a5a3a"),
        "MOTHER": ("#b5784a", "#d4a07a", "#7a4a30"),
        "SISTER": ("#d4a070", "#f0d0a8", "#a06a48"),
        "FRIEND": ("#b56c42", "#d49868", "#6e4028"),
    }
    skin, skin_hi, skin_sh = skins.get(key, ("#c48a5a", "#e8c39a", "#8a5a3a"))
    return {
        "key": key,
        "skin": skin,
        "skin_hi": skin_hi,
        "skin_sh": skin_sh,
        "primary": primary,
        "secondary": secondary,
        "tertiary": tertiary,
        "navy": palette["navy"],
        "gold": palette["gold"],
        "maroon": palette["maroon"],
        "peepal": palette["peepal"],
        "woman": key in {"MOTHER", "SISTER"},
        "age_lines": key == "MOTHER",
        "stubble": key in {"ADAM", "FRIEND"},
        "label": char.adapted_name or char.source_name,
        "grooming": (costume.grooming if costume else char.grooming) or "",
        "jewellery": (costume.jewellery if costume else "") or "",
        "footwear": (costume.footwear if costume else "") or "",
    }


def _figure_defs(uid: str, look: dict) -> str:
    p, s, t = look["primary"], look["secondary"], look["tertiary"]
    return f'''
  <radialGradient id="skin-{uid}" cx="38%" cy="32%" r="70%">
    <stop offset="0%" stop-color="{look["skin_hi"]}"/>
    <stop offset="55%" stop-color="{look["skin"]}"/>
    <stop offset="100%" stop-color="{look["skin_sh"]}"/>
  </radialGradient>
  <linearGradient id="cloth-{uid}" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{_tint(p, 22)}"/>
    <stop offset="45%" stop-color="{p}"/>
    <stop offset="100%" stop-color="{_shade(p, 28)}"/>
  </linearGradient>
  <linearGradient id="salwar-{uid}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{_tint(s, 12)}"/>
    <stop offset="100%" stop-color="{_shade(s, 30)}"/>
  </linearGradient>
  <linearGradient id="jacket-{uid}" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{_tint(t, 10)}"/>
    <stop offset="100%" stop-color="{_shade(t, 35)}"/>
  </linearGradient>
  <pattern id="check-{uid}" width="11" height="11" patternUnits="userSpaceOnUse">
    <rect width="11" height="11" fill="{p}"/>
    <rect width="5.5" height="5.5" fill="#3d4a28" opacity="0.42"/>
    <rect x="5.5" y="5.5" width="5.5" height="5.5" fill="#3d4a28" opacity="0.42"/>
  </pattern>
  <pattern id="phulkari-{uid}" width="16" height="16" patternUnits="userSpaceOnUse">
    <rect width="16" height="16" fill="{s}"/>
    <path d="M8,2 L10,8 L8,14 L6,8 Z" fill="{look["gold"]}" opacity="0.85"/>
    <circle cx="8" cy="8" r="1.6" fill="#f4ead4"/>
  </pattern>
  <filter id="soft-{uid}" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="0" dy="3" stdDeviation="2.4" flood-color="#1a120c" flood-opacity="0.28"/>
  </filter>
'''


def _person(look: dict, letter: str = "none", pose: str = "stand", uid: str = "p", extra: str = "") -> str:
    """Figure origin at the feet. Negative y is up."""
    key = look["key"]
    skin = f"url(#skin-{uid})"
    sit = pose == "sit"
    lean = pose == "lean"
    hip = -70 if sit else -108
    torso_top = hip - (58 if sit else 78)
    neck_y = torso_top - 9
    head_y = neck_y - 26
    lean_x = 10 if lean else 0

    shadow = f'<ellipse cx="2" cy="5" rx="36" ry="9" fill="#1c140e" opacity="0.32"/>'
    legs = _legs(look, uid, hip, sit)
    shoes = _shoes(look, key)
    torso = _torso(look, uid, hip, torso_top, key)
    arms = _arms(look, uid, hip, torso_top, key, lean)
    neck = f'<rect x="-6.5" y="{neck_y}" width="13" height="13" rx="5" fill="{skin}"/>'
    hair, head, earrings = _head_stack(look, uid, head_y, neck_y, hip, key)
    drape_back, drape_front = _dupatta(look, uid, head_y, hip, torso_top, key)
    letter_svg = _letter_prop(letter, hip)
    extra_svg = extra
    if extra == "phone":
        extra_svg = (
            f'<g transform="translate(26,{hip + 26})">'
            '<rect x="0" y="0" width="11" height="19" rx="2.2" fill="#1d1d1f"/>'
            '<rect x="1.2" y="2" width="8.6" height="13.5" rx="1" fill="#9ec9d6"/>'
            '<circle cx="5.5" cy="17.2" r="0.8" fill="#888"/>'
            "</g>"
        )

    sit_shift = "translate(0, 38)" if sit else ""
    lean_rot = f"rotate(-7 {lean_x} {hip})" if lean else ""
    return (
        f'<g class="figure-{key.lower()}" filter="url(#soft-{uid})" '
        f'transform="translate({lean_x},0) {sit_shift} {lean_rot}">'
        f"{shadow}{drape_back}{legs}{shoes}{torso}{arms}{neck}{hair}{head}{earrings}{drape_front}{letter_svg}{extra_svg}"
        "</g>"
    )


def _legs(look: dict, uid: str, hip: float, sit: bool) -> str:
    fill = f"url(#salwar-{uid})"
    if look["woman"]:
        if sit:
            return (
                f'<path d="M-24,-4 Q-48,-28 -30,{hip+8} L-6,{hip} L-8,-4 Z" fill="{fill}"/>'
                f'<path d="M8,-4 L10,{hip} L28,{hip+6} Q40,-20 24,-4 Z" fill="{fill}"/>'
                f'<path d="M-22,-6 Q0,-16 22,-6 L18,6 Q0,14 -18,6 Z" fill="{fill}"/>'
            )
        return (
            f'<path d="M-24,-4 Q-28,{hip+18} -16,{hip} L-3,{hip} L-6,-4 Z" fill="{fill}"/>'
            f'<path d="M6,-4 L8,{hip} L20,{hip} Q28,{hip+18} 24,-4 Z" fill="{fill}"/>'
            f'<path d="M-20,-8 Q0,-20 20,-8 L18,5 Q0,14 -18,5 Z" fill="{fill}"/>'
        )
    if sit:
        return (
            f'<path d="M-18,-4 L-36,-22 L-22,{hip} L-6,{hip} Z" fill="{fill}"/>'
            f'<path d="M6,-4 L8,{hip} L22,{hip} L40,-18 Z" fill="{fill}"/>'
        )
    return (
        f'<rect x="-19" y="{hip}" width="15" height="{abs(hip) - 5}" rx="7" fill="{fill}"/>'
        f'<rect x="4" y="{hip}" width="15" height="{abs(hip) - 5}" rx="7" fill="{fill}"/>'
        f'<path d="M-19,{hip+8} Q-8,{hip+40} -18,{hip+70}" fill="none" stroke="#000" stroke-opacity="0.08" stroke-width="2"/>'
    )


def _shoes(look: dict, key: str) -> str:
    if key == "FRIEND":
        return (
            '<ellipse cx="-12" cy="2" rx="17" ry="7.5" fill="#2f2c28"/>'
            '<ellipse cx="12" cy="2" rx="17" ry="7.5" fill="#2f2c28"/>'
            '<rect x="-27" y="-2" width="12" height="5" rx="1" fill="#5c5852"/>'
            '<rect x="15" y="-2" width="12" height="5" rx="1" fill="#5c5852"/>'
            '<path d="M-24,1 H0 M8,1 H24" stroke="#1a1816" stroke-width="0.6"/>'
        )
    if key == "SISTER":
        return (
            '<ellipse cx="-12" cy="3" rx="14" ry="5" fill="#6b3e28"/>'
            '<ellipse cx="12" cy="3" rx="14" ry="5" fill="#6b3e28"/>'
            f'<path d="M-20,2 Q-12,-2 -4,3" fill="none" stroke="{look["gold"]}" stroke-width="0.8" opacity="0.55"/>'
        )
    return (
        '<path d="M-30,2 Q-12,-9 3,3 Q-10,11 -30,7 Z" fill="#6b4226"/>'
        '<path d="M3,3 Q22,-9 30,2 Q22,11 3,7 Z" fill="#6b4226"/>'
        f'<path d="M-22,-1 Q-12,-7 -4,1" fill="none" stroke="{look["gold"]}" stroke-width="1.1" opacity="0.7"/>'
        f'<path d="M8,0 Q16,-7 24,1" fill="none" stroke="{look["gold"]}" stroke-width="1.1" opacity="0.7"/>'
    )


def _torso(look: dict, uid: str, hip: float, torso_top: float, key: str) -> str:
    cloth = f"url(#check-{uid})" if key == "FRIEND" else f"url(#cloth-{uid})"
    kameez = (
        f'<path d="M-31,{hip+7} L-35,{torso_top+10} Q-10,{torso_top-14} 0,{torso_top-10} Q10,{torso_top-14} 35,{torso_top+10} '
        f'L31,{hip+7} Q0,{hip+20} -31,{hip+7} Z" fill="{cloth}"/>'
        f'<path d="M-8,{torso_top+6} L-6,{hip+6} M8,{torso_top+6} L6,{hip+6}" stroke="#fff" stroke-width="0.6" opacity="0.22"/>'
        f'<path d="M0,{torso_top-2} L0,{hip+8}" stroke="#2b2118" stroke-width="0.7" opacity="0.18"/>'
    )
    buttons = "".join(
        f'<circle cx="0" cy="{torso_top + 16 + i * 14}" r="1.5" fill="{look["gold"]}" opacity="0.75"/>' for i in range(4)
    )
    if key == "FRIEND":
        buttons = f'<path d="M0,{torso_top+2} L0,{hip+4}" stroke="#2a3218" stroke-width="1.3"/>'
        vest = (
            f'<path d="M-18,{torso_top+8} L-16,{hip+6} L16,{hip+6} L18,{torso_top+8} Q0,{torso_top+18} -18,{torso_top+8} Z" '
            f'fill="#c8b48a" opacity="0.55"/>'
        )
        kameez = kameez + vest
    jacket = ""
    if key == "ADAM":
        jacket = (
            f'<path d="M-34,{torso_top+12} L-42,{hip+10} L-20,{hip+16} L-16,{torso_top+22} Z" fill="url(#jacket-{uid})"/>'
            f'<path d="M34,{torso_top+12} L42,{hip+10} L20,{hip+16} L16,{torso_top+22} Z" fill="url(#jacket-{uid})"/>'
            f'<path d="M-18,{torso_top+10} Q0,{torso_top+26} 18,{torso_top+10}" fill="none" stroke="#8a6a4a" stroke-width="1.2"/>'
            '<path d="M22,-150 L34,-118 L28,-116 L18,-146 Z" fill="#5a4030" opacity="0.35"/>'
        )
    return kameez + buttons + jacket


def _arms(look: dict, uid: str, hip: float, torso_top: float, key: str, lean: bool) -> str:
    sleeve = look["primary"] if key != "FRIEND" else look["primary"]
    skin = f"url(#skin-{uid})"
    left_end = hip + (18 if lean else 40)
    if look["woman"]:
        arms = (
            f'<path d="M-28,{torso_top+18} Q-44,{hip} -28,{hip+26}" fill="none" stroke="url(#cloth-{uid})" stroke-width="11" stroke-linecap="round"/>'
            f'<path d="M28,{torso_top+18} Q44,{hip} 28,{hip+26}" fill="none" stroke="url(#cloth-{uid})" stroke-width="11" stroke-linecap="round"/>'
            f'<circle cx="-28" cy="{hip+28}" r="6.4" fill="{skin}"/>'
            f'<circle cx="28" cy="{hip+28}" r="6.4" fill="{skin}"/>'
        )
        if key == "MOTHER":
            arms += (
                f'<g transform="translate(-28,{hip+26})">'
                + "".join(f'<circle cx="{i * 3.1}" cy="0" r="2.3" fill="#f3ead6"/>' for i in range(-2, 3))
                + "</g>"
            )
        return arms
    return (
        f'<path d="M-32,{torso_top+16} Q-50,{hip+8} -38,{left_end}" fill="none" stroke="{sleeve}" stroke-width="12" stroke-linecap="round"/>'
        f'<path d="M32,{torso_top+16} Q50,{hip+8} 40,{hip+40}" fill="none" stroke="{sleeve}" stroke-width="12" stroke-linecap="round"/>'
        f'<circle cx="-38" cy="{left_end + 2}" r="7.2" fill="{skin}"/>'
        f'<circle cx="40" cy="{hip+42}" r="7.2" fill="{skin}"/>'
        f'<circle cx="-38" cy="{left_end + 2}" r="8.4" fill="none" stroke="{look["gold"]}" stroke-width="2.6"/>'
        f'<circle cx="-38" cy="{left_end + 2}" r="6.6" fill="none" stroke="#c9a227" stroke-width="0.7" opacity="0.7"/>'
    )


def _head_stack(look: dict, uid: str, head_y: float, neck_y: float, hip: float, key: str) -> tuple[str, str, str]:
    skin = f"url(#skin-{uid})"
    head = (
        f'<ellipse cx="0" cy="{head_y}" rx="21" ry="25.5" fill="{skin}"/>'
        f'<ellipse cx="-16.5" cy="{head_y+3}" rx="4.8" ry="6.2" fill="{skin}"/>'
        f'<ellipse cx="16.5" cy="{head_y+3}" rx="4.8" ry="6.2" fill="{skin}"/>'
        f'<path d="M-11,{head_y-8} Q-8,{head_y-11} -4,{head_y-8}" fill="none" stroke="#3a2418" stroke-width="1.7" stroke-linecap="round"/>'
        f'<path d="M4,{head_y-8} Q8,{head_y-11} 11,{head_y-8}" fill="none" stroke="#3a2418" stroke-width="1.7" stroke-linecap="round"/>'
        f'<ellipse cx="-7.5" cy="{head_y-1.5}" rx="5.4" ry="3.1" fill="#fff8ee"/>'
        f'<ellipse cx="7.5" cy="{head_y-1.5}" rx="5.4" ry="3.1" fill="#fff8ee"/>'
        f'<ellipse cx="-7.5" cy="{head_y-1.4}" rx="2.3" ry="2.5" fill="#3b2418"/>'
        f'<ellipse cx="7.5" cy="{head_y-1.4}" rx="2.3" ry="2.5" fill="#3b2418"/>'
        f'<circle cx="-6.7" cy="{head_y-2.1}" r="0.7" fill="#fff"/>'
        f'<circle cx="8.3" cy="{head_y-2.1}" r="0.7" fill="#fff"/>'
        f'<path d="M0,{head_y+1} Q2.2,{head_y+8} 0,{head_y+11} Q-1.6,{head_y+8} 0,{head_y+1}" fill="{look["skin_sh"]}" opacity="0.55"/>'
        f'<path d="M-6.5,{head_y+14.5} Q0,{head_y+17.8} 6.5,{head_y+14.5}" fill="none" stroke="#8a4a38" stroke-width="1.45" stroke-linecap="round"/>'
        f'<path d="M-5.5,{head_y+13.6} Q0,{head_y+15.4} 5.5,{head_y+13.6}" fill="none" stroke="#c47a68" stroke-width="0.8" opacity="0.7"/>'
    )
    if look["age_lines"]:
        head += (
            f'<path d="M-15,{head_y-7} Q-11,{head_y-5} -8,{head_y-7}" fill="none" stroke="#8a5a44" stroke-width="0.7" opacity="0.55"/>'
            f'<path d="M8,{head_y-7} Q11,{head_y-5} 15,{head_y-7}" fill="none" stroke="#8a5a44" stroke-width="0.7" opacity="0.55"/>'
            f'<path d="M-14,{head_y+8} Q-11,{head_y+10} -9,{head_y+8}" fill="none" stroke="#8a5a44" stroke-width="0.6" opacity="0.4"/>'
        )
    if look["stubble"]:
        head += f'<ellipse cx="0" cy="{head_y+16}" rx="11.5" ry="6.2" fill="#4a3224" opacity="0.42"/>'
    if key == "FRIEND":
        head += f'<path d="M-11,{head_y+11} Q0,{head_y+21} 11,{head_y+11} Q0,{head_y+16} -11,{head_y+11}" fill="#4a2e20" opacity="0.82"/>'

    hair = ""
    if key == "ADAM":
        hair = (
            f'<ellipse cx="0" cy="{head_y-14}" rx="23" ry="16" fill="{look["navy"]}"/>'
            f'<ellipse cx="1" cy="{head_y-24}" rx="17" ry="11" fill="{_shade(look["navy"], 10)}"/>'
            f'<path d="M-22,{head_y-6} Q-27,{head_y+8} -14,{head_y+12} Q-20,{head_y} -18,{head_y-8}" fill="{look["navy"]}"/>'
            f'<path d="M18,{head_y-8} Q26,{head_y+4} 16,{head_y+11}" fill="{look["navy"]}"/>'
            f'<ellipse cx="3" cy="{head_y-28}" rx="9" ry="5.5" fill="{look["gold"]}"/>'
            f'<circle cx="3" cy="{head_y-28}" r="2.1" fill="#1e3354"/>'
            f'<path d="M-10,{head_y-6} Q0,{head_y-12} 12,{head_y-5}" fill="none" stroke="#0f1c30" stroke-width="1.2" opacity="0.35"/>'
        )
    elif key == "FRIEND":
        hair = (
            f'<path d="M-20,{head_y-6} Q0,{head_y-24} 20,{head_y-6} L18,{head_y-16} Q0,{head_y-22} -18,{head_y-16} Z" fill="#2a1c14"/>'
            f'<rect x="-19" y="{head_y-22}" width="38" height="11" rx="3" fill="{look["peepal"]}"/>'
            f'<rect x="-20" y="{head_y-24}" width="40" height="5" rx="2" fill="#2f4a2a"/>'
        )
    elif key == "MOTHER":
        hair = (
            f'<ellipse cx="0" cy="{head_y-12}" rx="23" ry="13" fill="#2e2218"/>'
            f'<circle cx="0" cy="{head_y-20}" r="8.5" fill="#3d3024"/>'
            f'<path d="M-5,{head_y-22} L5,{head_y-22}" stroke="#c8c0b4" stroke-width="1.4"/>'
            f'<path d="M-3,{head_y-18} Q0,{head_y-16} 3,{head_y-18}" fill="none" stroke="#c8c0b4" stroke-width="0.8" opacity="0.7"/>'
        )
    elif key == "SISTER":
        hair = (
            f'<ellipse cx="0" cy="{head_y-13}" rx="22" ry="12" fill="#241810"/>'
            f'<path d="M-18,{head_y-6} Q-24,{head_y+36} -7,{hip+18}" fill="#241810"/>'
            f'<path d="M-8,{hip+16} Q-5,{hip+42} -7,{hip+50}" stroke="#241810" stroke-width="5.5" fill="none" stroke-linecap="round"/>'
            f'<path d="M-20,{head_y-1} L20,{head_y-1}" stroke="#1a120c" stroke-width="1.8"/>'
            f'<circle cx="-7" cy="{hip+50}" r="3.2" fill="#241810"/>'
        )

    earrings = ""
    if key == "MOTHER":
        earrings = (
            f'<circle cx="-18" cy="{head_y+8}" r="3.3" fill="{look["gold"]}"/>'
            f'<circle cx="18" cy="{head_y+8}" r="3.3" fill="{look["gold"]}"/>'
            f'<circle cx="0" cy="{neck_y+9}" r="2.5" fill="{look["gold"]}"/>'
            f'<circle cx="0" cy="{neck_y+9}" r="1.1" fill="#f4ead4"/>'
        )
    elif key == "SISTER":
        earrings = (
            f'<circle cx="-17.5" cy="{head_y+6}" r="2.1" fill="{look["gold"]}"/>'
            f'<circle cx="17.5" cy="{head_y+6}" r="2.1" fill="{look["gold"]}"/>'
        )
    return hair, head, earrings


def _dupatta(look: dict, uid: str, head_y: float, hip: float, torso_top: float, key: str) -> tuple[str, str]:
    if key == "MOTHER":
        back = (
            f'<path d="M-20,{head_y-18} Q-48,{head_y} -58,{hip} Q-20,{hip+48} 20,{hip+20} Q52,{torso_top} 22,{head_y-10} '
            f'Q8,{head_y-28} -20,{head_y-18} Z" fill="url(#phulkari-{uid})" opacity="0.96"/>'
        )
        front = (
            f'<path d="M-16,{head_y+4} Q-4,{torso_top+28} 10,{hip+6}" fill="none" stroke="{look["gold"]}" stroke-width="2.2" opacity="0.65"/>'
        )
        return back, front
    if key == "SISTER":
        back = (
            f'<path d="M16,{torso_top-2} Q52,{hip-8} 30,{hip+42} Q-8,{hip+18} -22,{torso_top+16} Q8,{torso_top+8} 16,{torso_top-2} Z" '
            f'fill="#e7b7c2" opacity="0.9"/>'
            f'<path d="M18,{torso_top+6} Q36,{hip+10} 24,{hip+36}" fill="none" stroke="#fff" stroke-width="1" opacity="0.35"/>'
        )
        return back, ""
    return "", ""


def _letter_prop(letter: str, hip: float) -> str:
    envelope = (
        '<rect x="0" y="0" width="22" height="14" rx="1.2" fill="#f7f1de" stroke="#7a1f2b" stroke-width="1.3"/>'
        '<path d="M0,0 L11,8 L22,0" fill="none" stroke="#7a1f2b" stroke-width="1.2"/>'
        '<path d="M0,14 L8,8 M22,14 L14,8" fill="none" stroke="#7a1f2b" stroke-width="0.6" opacity="0.5"/>'
    )
    if letter == "pocket":
        return f'<g id="letter-pocket" transform="translate(12,-152)">{envelope}</g>'
    if letter == "hand":
        return f'<g id="letter-hand" transform="translate(34,{hip+26})">{envelope}</g>'
    return ""


def _character_svg(char, costume, palette, seed, choice: CultureChoice) -> str:
    look = _look(char, costume, palette)
    uid = char.character_id.lower()
    letter = "hand" if char.source_name.upper() == "ADAM" else "none"
    notes = [
        f"Age {char.age or '—'} · {char.role}",
        look["grooming"],
        look["jewellery"],
        f"{choice.culture_id} / {choice.setting} · same face in every scene",
    ]
    note_svg = "".join(
        f'<text x="28" y="{518 + i * 15}" font-family="Georgia" font-size="11" fill="#3b2a1a">{_xml(n[:58])}</text>'
        for i, n in enumerate(notes)
        if n
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 640" width="420" height="640">
  {_studio_defs(palette)}
  <defs>{_figure_defs(uid, look)}</defs>
  <rect width="420" height="640" fill="url(#studio)"/>
  <rect x="0" y="0" width="420" height="640" filter="url(#grain)" opacity="0.55"/>
  <rect x="16" y="16" width="388" height="608" fill="none" stroke="{palette["gold"]}" stroke-width="2"/>
  <text x="210" y="46" text-anchor="middle" font-family="Georgia" font-size="20" fill="{palette["navy"]}">{_xml(look["label"])}</text>
  <text x="210" y="66" text-anchor="middle" font-family="Georgia" font-size="11" fill="{palette["brick"]}">{_xml(char.character_id)} · {char.source_name} · seed {seed}</text>
  <ellipse cx="210" cy="478" rx="96" ry="20" fill="#2b2118" opacity="0.16"/>
  <g transform="translate(210,468) scale(1.62)">{_person(look, letter=letter, uid=uid)}</g>
  {note_svg}
  <text x="210" y="612" text-anchor="middle" font-family="Georgia" font-size="10" fill="{palette["navy"]}">{_xml((costume.garments if costume else "")[:70])}</text>
</svg>'''


def _costume_svg(char, costume, palette, choice: CultureChoice) -> str:
    look = _look(char, costume, palette)
    uid = costume.costume_id.lower()
    swatches = "".join(
        f'<g transform="translate({36 + i * 86}, 86)">'
        f'<rect width="74" height="46" rx="5" fill="{_colour(col, palette)}" stroke="#3b2a1a"/>'
        f'<text x="37" y="62" text-anchor="middle" font-size="11" font-family="Georgia">{_xml(col)}</text>'
        f"</g>"
        for i, col in enumerate((costume.colours or ["dust"])[:4])
    )
    rows = [
        ("Garments", costume.garments),
        ("Fabrics", costume.fabrics),
        ("Footwear", costume.footwear),
        ("Jewellery", costume.jewellery),
        ("Grooming", costume.grooming),
        ("Scenes", ", ".join(costume.scenes) + " — one variant, reused"),
        ("Change", costume.change_reason),
    ]
    body = "".join(
        f'<text x="28" y="{178 + i * 30}" font-family="Georgia" font-size="13" fill="#1e3354">'
        f'<tspan font-weight="bold">{_xml(label)}:</tspan> {_xml((value or "—")[:78])}</text>'
        for i, (label, value) in enumerate(rows)
    )
    fabric = (
        f'<g transform="translate(430,86)">'
        f'<rect width="150" height="110" fill="url(#phulkari-{uid})" stroke="#3b2a1a"/>'
        f'<text x="75" y="128" text-anchor="middle" font-size="10" font-family="Georgia">fabric detail</text>'
        f"</g>"
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 820 540" width="820" height="540">
  {_studio_defs(palette)}
  <defs>{_figure_defs(uid, look)}</defs>
  <rect width="820" height="540" fill="#f7f0e2"/>
  <rect x="12" y="12" width="796" height="516" fill="none" stroke="{palette["gold"]}" stroke-width="2"/>
  <text x="28" y="42" font-family="Georgia" font-size="22" fill="#1e3354">{_xml(costume.costume_id)}</text>
  <text x="28" y="66" font-family="Georgia" font-size="13" fill="#7a1f2b">{_xml(char.adapted_name)} · {_xml(costume.label)} · {choice.culture_id}</text>
  {swatches}
  {fabric}
  {body}
  <g transform="translate(690,445) scale(1.22)">{_person(look, letter="pocket" if char.source_name.upper()=="ADAM" else "none", uid=uid)}</g>
</svg>'''


def _scene_svg(scene, characters, costumes, palette, choice: CultureChoice) -> str:
    present = [c for c in characters if c.character_id in scene.characters and c.source_name.upper() != "UNCLE"]
    costume_map = {c.character_id: c for c in costumes}
    loc = scene.location.upper()
    urban = choice.setting == "urban"
    letter_on_table = scene.scene_id == "SC04"
    if "YARD" in loc or "FRONT" in loc:
        bg = _set_aangan(palette, urban)
    elif "KITCHEN" in loc:
        bg = _set_rasoi(palette)
    elif "MARKET" in loc or "STREET" in loc:
        bg = _set_mandi(palette, urban)
    else:
        bg = _set_baithak(palette, letter_on_table)

    figures = []
    figure_defs = []
    slots = _blocking(scene.scene_id, present)
    for char, (x, scale, pose) in slots:
        costume = costume_map.get(char.character_id)
        look = _look(char, costume, palette)
        letter = "none"
        extra = ""
        if char.source_name.upper() == "ADAM":
            if scene.scene_id == "SC01":
                letter = "hand"
            elif scene.scene_id in {"SC02", "SC03"}:
                letter = "pocket"
        if char.source_name.upper() == "SISTER" and scene.scene_id == "SC01":
            extra = "phone"
        uid = f"{scene.scene_id}-{char.character_id}".lower()
        figure_defs.append(_figure_defs(uid, look))
        figures.append(
            f'<g transform="translate({x},458) scale({scale})">{_person(look, letter=letter, pose=pose, uid=uid, extra=extra)}</g>'
        )
        first = (char.adapted_name or char.source_name).split()[0]
        figures.append(
            f'<text x="{x}" y="508" text-anchor="middle" font-family="Georgia" font-size="13" fill="#1e3354">{_xml(first)}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540">
  {_studio_defs(palette)}
  <defs>{''.join(figure_defs)}</defs>
  {bg}
  {''.join(figures)}
  <rect x="0" y="0" width="960" height="540" filter="url(#grain)" opacity="0.28"/>
  <rect x="0" y="0" width="960" height="66" fill="#14110e" opacity="0.72"/>
  <text x="22" y="30" font-family="Georgia" font-size="20" fill="#f4ead7">{scene.scene_id} · {_xml(scene.int_ext)} {_xml(scene.time)}</text>
  <text x="22" y="52" font-family="Georgia" font-size="13" fill="#e8d5b5">{_xml(scene.location)} · {choice.culture_id}/{choice.setting} · {_xml(scene.mood)}</text>
</svg>'''


def _blocking(scene_id: str, present: list[CharacterRecord]) -> list[tuple[CharacterRecord, tuple[int, float, str]]]:
    order = {c.source_name.upper(): c for c in present}
    if scene_id == "SC01":
        layout = [("MOTHER", (190, 1.08, "stand")), ("ADAM", (430, 1.22, "stand")), ("SISTER", (690, 0.98, "sit"))]
    elif scene_id == "SC02":
        layout = [("FRIEND", (170, 1.08, "lean")), ("ADAM", (380, 1.18, "sit")), ("SISTER", (560, 1.02, "stand")), ("MOTHER", (760, 1.12, "stand"))]
    elif scene_id == "SC03":
        layout = [("ADAM", (330, 1.24, "stand")), ("FRIEND", (580, 1.16, "stand"))]
    else:
        layout = [("MOTHER", (240, 1.08, "sit")), ("ADAM", (470, 1.22, "stand")), ("SISTER", (710, 1.06, "stand"))]
    out = []
    for key, slot in layout:
        if key in order:
            out.append((order[key], slot))
    for char in present:
        if char.source_name.upper() not in {k for k, _ in layout}:
            out.append((char, (780, 1.0, "stand")))
    return out


def _set_aangan(palette, urban: bool) -> str:
    wall = "#8f5a3c" if urban else palette["brick"]
    leaves = "".join(
        f'<ellipse cx="{740 + (i % 5) * 18}" cy="{210 + (i // 5) * 16}" rx="16" ry="11" fill="{palette["peepal"] if i % 2 == 0 else "#2f4a2c"}" opacity="0.9"/>'
        for i in range(14)
    )
    bricks = "".join(
        f'<rect x="{48 + col * 28}" y="{128 + row * 16}" width="26" height="14" fill="none" stroke="#6e3b28" stroke-width="0.6" opacity="0.35"/>'
        for row in range(10)
        for col in range(10)
    )
    return f'''
  <rect width="960" height="540" fill="url(#dawn)"/>
  <ellipse cx="780" cy="78" rx="78" ry="78" fill="#f7e0b4" opacity="0.9"/>
  <ellipse cx="780" cy="78" rx="48" ry="48" fill="#ffe9c2" opacity="0.55"/>
  <rect y="312" width="960" height="228" fill="{palette["earth"]}"/>
  <path d="M0,312 Q90,294 180,308 Q280,326 400,300 Q560,276 960,318 L960,370 L0,370 Z" fill="#6f8a4a" opacity="0.62"/>
  <rect x="40" y="112" width="300" height="210" fill="{wall}"/>
  {bricks}
  <rect x="40" y="100" width="300" height="16" fill="#d9c4a0"/>
  <rect x="56" y="128" width="68" height="50" fill="#cfe4ef" opacity="0.55"/>
  <rect x="154" y="128" width="68" height="50" fill="#cfe4ef" opacity="0.4"/>
  <rect x="252" y="128" width="68" height="50" fill="#cfe4ef" opacity="0.55"/>
  <rect x="156" y="214" width="46" height="108" fill="#3b2a1a"/>
  <rect x="22" y="248" width="16" height="118" fill="#4a4a48"/>
  <rect x="22" y="246" width="78" height="9" fill="#6a6a66"/>
  {leaves}
  <rect x="746" y="250" width="18" height="96" fill="#5a3a22"/>
  <rect x="560" y="278" width="126" height="16" rx="3" fill="#c4a574"/>
  <rect x="568" y="270" width="110" height="10" fill="#a98452"/>
  <path d="M0,430 Q240,418 480,436 Q720,450 960,428 L960,540 L0,540 Z" fill="#5a4632" opacity="0.18"/>
'''


def _set_rasoi(palette) -> str:
    steam = "".join(
        f'<path d="M{228 + i * 12},214 Q{214 + i * 12},{176 - i * 10} {232 + i * 10},{148 - i * 8}" fill="none" stroke="#e8eef1" stroke-width="3.2" opacity="0.5"/>'
        for i in range(4)
    )
    glasses = "".join(
        f'<rect x="{300 + i * 48}" y="226" width="34" height="24" rx="3" fill="#c5c9cc" stroke="#8a9094"/>'
        f'<rect x="{304 + i * 48}" y="230" width="26" height="8" fill="#d8dde0"/>'
        for i in range(3)
    )
    return f'''
  <rect width="960" height="540" fill="#ead9b8"/>
  <rect y="312" width="960" height="228" fill="#c9a87a"/>
  <rect x="0" y="78" width="960" height="234" fill="#d4b892"/>
  <rect x="28" y="118" width="240" height="164" fill="#6b5340"/>
  <rect x="48" y="148" width="86" height="56" fill="#2b2b2b"/>
  <rect x="54" y="154" width="74" height="20" fill="#c45c3a"/>
  <ellipse cx="228" cy="204" rx="30" ry="17" fill="#b8b8b8"/>
  <rect x="216" y="186" width="11" height="24" fill="#9a9a9a"/>
  {steam}
  <rect x="286" y="252" width="300" height="20" fill="#7a5a3a"/>
  {glasses}
  <rect x="680" y="108" width="230" height="204" fill="#5a4030"/>
  <rect x="702" y="130" width="80" height="56" fill="#3b2a1a"/>
  <rect x="802" y="130" width="80" height="56" fill="#3b2a1a"/>
  <ellipse cx="140" cy="300" rx="40" ry="10" fill="#8a6a3a" opacity="0.4"/>
'''


def _set_mandi(palette, urban: bool) -> str:
    sky = palette["sky_afternoon"]
    shop = "#8a3b22" if urban else "#a45a3c"
    awnings = "".join(
        f'<path d="M{x},118 L{x + 150},118 L{x + 150},138 L{x},150 Z" fill="{fill}" opacity="0.92"/>'
        for x, fill in ((24, shop), (210, "#6b5340"), (390, "#7a1f2b"), (580, "#3d5c3a"))
    )
    return f'''
  <rect width="960" height="540" fill="{sky}"/>
  <rect y="258" width="960" height="282" fill="#c4a060"/>
  <path d="M0,258 L960,258 L960,278 L0,298 Z" fill="#b08950" opacity="0.45"/>
  <rect x="24" y="118" width="150" height="160" fill="{shop}"/>
  <rect x="210" y="128" width="150" height="150" fill="#6b5340"/>
  <rect x="390" y="108" width="170" height="170" fill="#7a1f2b"/>
  <rect x="580" y="136" width="150" height="142" fill="#3d5c3a"/>
  {awnings}
  <text x="99" y="168" text-anchor="middle" font-size="13" fill="#f4ead7" font-family="Georgia">kiryana</text>
  <rect x="48" y="178" width="52" height="100" fill="#3b2a1a"/>
  <rect x="418" y="158" width="42" height="74" fill="#2b2118"/>
  <rect x="760" y="168" width="150" height="96" rx="10" fill="#c47a4a"/>
  <circle cx="786" cy="276" r="18" fill="#2b2b2b"/>
  <circle cx="886" cy="276" r="18" fill="#2b2b2b"/>
  <circle cx="830" cy="214" r="8" fill="#f4ead7"/>
  <circle cx="660" cy="308" r="16" fill="#2b2b2b"/>
  <path d="M660,308 L660,246 L726,234" fill="none" stroke="#2b2b2b" stroke-width="4"/>
  <rect x="268" y="308" width="96" height="42" fill="#d9c4a0"/>
  <ellipse cx="316" cy="308" rx="32" ry="11" fill="#e8d5b5"/>
  <text x="316" y="336" text-anchor="middle" font-size="10" fill="#3b2a1a" font-family="Georgia">chai</text>
'''


def _set_baithak(palette, letter_on_table: bool) -> str:
    letter = ""
    if letter_on_table:
        letter = '''
  <g id="letter-table" transform="translate(448,336)">
    <rect width="40" height="24" rx="2" fill="#f7f1de" stroke="#7a1f2b" stroke-width="1.7"/>
    <path d="M0,0 L20,13 L40,0" fill="none" stroke="#7a1f2b"/>
    <text x="20" y="42" text-anchor="middle" font-size="12" font-family="Georgia" fill="#7a1f2b">chiTThi</text>
  </g>'''
    return f'''
  <rect width="960" height="540" fill="#3a281c"/>
  <rect y="70" width="960" height="250" fill="#ead9b8"/>
  <rect y="312" width="960" height="228" fill="#6b4226"/>
  <rect x="46" y="92" width="130" height="86" fill="#cfe4ef" opacity="0.4"/>
  <rect x="780" y="90" width="130" height="170" fill="#3b2a1a"/>
  <rect x="798" y="112" width="94" height="76" fill="#1e3354"/>
  <circle cx="845" cy="208" r="20" fill="#d4a017" opacity="0.85"/>
  <circle cx="845" cy="208" r="8" fill="#f4ead4" opacity="0.5"/>
  <rect x="90" y="248" width="150" height="74" rx="6" fill="{palette["maroon"]}"/>
  <rect x="108" y="234" width="114" height="22" rx="6" fill="#5a1820"/>
  <rect x="400" y="322" width="156" height="16" rx="3" fill="#8a6a3a"/>
  <rect x="414" y="312" width="128" height="12" fill="#c4a574"/>
  {letter}
  <path d="M210,312 Q460,288 780,312 L780,372 L210,372 Z" fill="#7a1f2b" opacity="0.22"/>
'''


def _studio_defs(palette: dict) -> str:
    return f'''<defs>
  <linearGradient id="studio" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#f6ead0"/>
    <stop offset="55%" stop-color="{palette["dust"]}"/>
    <stop offset="100%" stop-color="#c9ae86"/>
  </linearGradient>
  <linearGradient id="dawn" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#f7d3a1"/>
    <stop offset="100%" stop-color="{palette["sky_morning"]}"/>
  </linearGradient>
  <filter id="grain">
    <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="2"/>
    <feColorMatrix type="saturate" values="0"/>
    <feComponentTransfer><feFuncA type="linear" slope="0.07"/></feComponentTransfer>
  </filter>
</defs>'''


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (30, 51, 84)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def _tint(hex_color: str, amount: int) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(r + amount, g + amount, b + amount)


def _shade(hex_color: str, amount: int) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(r - amount, g - amount, b - amount)


def _colour(name: str, palette: dict) -> str:
    key = name.lower().replace(" ", "_")
    mapping = {
        "off-white": "#f3efe4",
        "navy": palette["navy"],
        "dust tan": palette["dust"],
        "maroon": palette["maroon"],
        "gold": palette["gold"],
        "cream": "#f4ead4",
        "mint": palette["mint"],
        "white": "#f8f6f0",
        "soft pink": "#e7b7c2",
        "olive check": "#6b7a45",
        "khaki": "#c6b17a",
        "beige": "#d7c4a3",
        "denim": "#4d6d8b",
        "mustard": palette["gold"],
        "orange": "#d1691a",
        "yellow": "#e6c84a",
        "grey": "#8a8f84",
        "dust": palette["dust"],
    }
    return mapping.get(name, mapping.get(key, palette.get(key, palette["navy"])))


def _xml(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
