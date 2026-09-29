from __future__ import annotations

import re

from .models import AdaptationDecision, AdaptationPlan, CharacterRecord, CultureChoice, SceneRecord

GURMUKHI_MAP = {
    "Bebe": "ਬੇਬੇ",
    "puttar": "ਪੁੱਤਰ",
    "Jaswant": "ਜਸਵੰਤ",
    "Simran": "ਸਿਮਰਨ",
    "Harpreet": "ਹਰਪ੍ਰੀਤ",
    "Happy": "ਹੈਪੀ",
    "Mama": "ਮਾਮਾ",
    "Jagtar": "ਜਗਤਾਰ",
    "chiTThi": "ਚਿੱਠੀ",
    "chitthi": "ਚਿੱਠੀ",
    "aangan": "ਆਂਗਣ",
    "rasoi": "ਰਸੋਈ",
    "baithak": "ਬੈਠਕ",
    "pind": "ਪਿੰਡ",
    "yaar": "ਯਾਰ",
    "Sat sri akaal": "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ",
    "kothi": "ਕੋਠੀ",
}


def build_adaptation_plan(
    culture_choice: CultureChoice,
    culture: dict,
    characters: list[CharacterRecord],
    scenes: list[SceneRecord],
) -> AdaptationPlan:
    setting_note = "rural Majha kothi and mandi road" if culture_choice.setting == "rural" else "urban Amritsar lane house and Hall Bazaar edge"
    decisions = [
        AdaptationDecision(
            decision_id="D01",
            topic="names",
            source="Adam, Mother, Sister, Friend, Uncle",
            adapted=", ".join(f"{c.source_name}→{c.adapted_name or c.source_name}" for c in characters),
            reason="Majhi kinship and village izzat need specific names, not generic North Indian labels.",
        ),
        AdaptationDecision(
            decision_id="D02",
            topic="work and stakes",
            source="an unnamed shop and a course",
            adapted="Mama Jagtar's kiryana on the pind chowk versus Jaswant's remaining college year",
            reason="The conflict is izzat and mother's brother's trust, not a generic career plot.",
        ),
        AdaptationDecision(
            decision_id="D03",
            topic="verbal texture",
            source="neutral English dialogue",
            adapted="Majhi-Roman (and optional Gurmukhi) with Bebe, puttar, chiTThi, rasoi, baithak",
            reason="Kinship and household space carry the drama; vocabulary-only translation would fail.",
        ),
        AdaptationDecision(
            decision_id="D04",
            topic="non-verbal",
            source="standing in a yard, sitting in a kitchen",
            adapted="Bebe in the doorway with covered head; no one takes her baithak chair until she nods; letter placed on the low table, not handed in the street",
            reason=culture["gestures"]["respect"],
        ),
        AdaptationDecision(
            decision_id="D05",
            topic="visual world",
            source="house, kitchen, market, living room",
            adapted=setting_note,
            reason="Exact Majha architecture, phulkari-border dupatta, kara, juttis, steel glasses.",
        ),
        AdaptationDecision(
            decision_id="D06",
            topic="humour",
            source="lost a bet joke",
            adapted="Yaar teasing about a lost shart, never mocking the dialect itself",
            reason=culture["humour"],
        ),
        AdaptationDecision(
            decision_id="D07",
            topic="story preservation",
            source="concealment → pressure → public temptation → admission",
            adapted="Same arc. Public refusal is culturally worse, so Scene 3 pushes him home rather than changing his goal.",
            reason="Cultural change must not reverse Adam's motivation.",
        ),
    ]
    uncertain = list(culture.get("uncertainty", []))
    if culture_choice.setting == "urban":
        uncertain.append("Urban Amritsar may code-switch more English; rural register is slightly relaxed but Bebe is kept.")
    return AdaptationPlan(
        culture=culture_choice,
        summary=(
            f"Adapt the letter drama into {culture['label']} ({culture_choice.setting} {culture_choice.region}). "
            "Household spaces (aangan, rasoi, baithak) remain the moral engine. Dialect is never the joke."
        ),
        decisions=decisions,
        uncertain_choices=uncertain,
        approved=False,
    )


def adapt_screenplay(
    source_text: str,
    scenes: list[SceneRecord],
    characters: list[CharacterRecord],
    culture: dict,
    culture_choice: CultureChoice,
) -> tuple[str, str, list[dict]]:
    name_map = {c.source_name.upper(): c.adapted_name for c in characters if c.adapted_name}
    loc_map = culture.get("locations", {})
    change_log: list[dict] = []
    pages: list[str] = [
        "CHITthi JO NAHI KHOLI",
        f"Majhi adaptation — {culture_choice.setting} {culture['region']}",
        f"Output script: {culture_choice.script}",
        "",
    ]
    for scene in scenes:
        loc_meta = _location_meta(scene.location, loc_map)
        loc_name = loc_meta.get("adapted", scene.location)
        architecture = loc_meta.get("architecture") if culture_choice.setting == "rural" else loc_meta.get("urban_variant", loc_meta.get("architecture", ""))
        heading = f"{scene.int_ext}. {loc_name.upper()} - {scene.time.upper() or 'DAY'}"
        pages.append(f"SCENE {scene.scene_number}")
        pages.append(heading)
        pages.append("")
        pages.append(architecture)
        pages.append("")
        change_log.append(
            {
                "scene_id": scene.scene_id,
                "kind": "location",
                "source": scene.location,
                "adapted": loc_name,
                "reason": "Exact Majha place identity rather than a generic Indian house.",
            }
        )
        for action in scene.action_lines:
            adapted_action = _adapt_action(action, name_map, culture, culture_choice)
            pages.append(adapted_action)
            if adapted_action != action:
                change_log.append(
                    {
                        "scene_id": scene.scene_id,
                        "kind": "action",
                        "source": action,
                        "adapted": adapted_action,
                        "reason": "Gesture, prop, and spatial behaviour rewritten for Majhi household etiquette.",
                    }
                )
        pages.append("")
        for line in scene.dialogue:
            speaker = next((c for c in characters if c.character_id == line["speaker"]), None)
            spoken_name = (speaker.adapted_name if speaker else line["source_name"]).split("(")[0].strip()
            adapted = _adapt_dialogue(
                line["text"], line.get("source_name", ""), culture, name_map, culture_choice.culture_id
            )
            pages.append(f"                    {spoken_name.upper()}")
            wrapped = _wrap(adapted, 52)
            for w in wrapped:
                pages.append(f"          {w}")
            pages.append("")
            change_log.append(
                {
                    "scene_id": scene.scene_id,
                    "kind": "dialogue",
                    "source": f"{line.get('source_name')}: {line['text']}",
                    "adapted": f"{spoken_name}: {adapted}",
                    "reason": _dialogue_reason(line.get("source_name", ""), line["text"]),
                }
            )
        pages.append("")
    pages.append("END.")
    roman = "\n".join(pages)
    gurmukhi = _to_gurmukhi(roman)
    chosen = gurmukhi if culture_choice.script == "gurmukhi" else roman
    return chosen, gurmukhi, change_log


def _location_meta(location: str, loc_map: dict) -> dict:
    key = location.upper()
    for src, meta in loc_map.items():
        if src in key or key in src:
            return meta
    return {}


def _adapt_action(text: str, name_map: dict, culture: dict, choice) -> str:
    out = text
    mother = "Bebe" if choice.culture_id == "majhi" else ("Maa" if choice.culture_id == "malwai" else "Mother")
    adam = name_map.get("ADAM", "Jaswant").split()[0]
    sister = name_map.get("SISTER", "Simran").split()[0]
    friend = name_map.get("FRIEND", "Harpreet").split()[0]
    replacements = [
        (r"\bAdam\b", adam),
        (r"\bMother\b", mother),
        (r"\bSister\b", sister),
        (r"\bFriend\b", friend),
        (r"\buncles?\b", "Mama"),
        (r"\bjacket pocket\b", "jacket de pocket" if choice.culture_id == "majhi" else "jacket pocket"),
        (r"\bjacket\b", "khaddar jacket" if choice.culture_id == "majhi" else "jacket"),
        (r"low wall\b", "aangan di kandh" if choice.culture_id == "majhi" else "sahn di kandh"),
        (r"doorway\b", "verandah de darwaze"),
        (r"shawl\b", "phulkari-border dupatta" if choice.culture_id == "majhi" else "dupatta"),
        (r"\bkitchen\b", "rasoi"),
        (r"metal gate\b", "lohe da gate"),
        (r"two-storey house\b", "do-manzila kothi" if choice.culture_id == "majhi" else "haveli"),
        (r"living room\b", "baithak"),
        (r"main chair\b", f"{mother} di kursi"),
        (r"low table\b", "chhoti mez"),
        (r"tea stall\b", "kulche-chole di reri" if choice.culture_id == "majhi" else "mandi stall"),
        (r"market\b", "pind da chowk" if choice.culture_id == "majhi" else "mandi sadak"),
        (r"phone\b", "mobile"),
        (r"cups\b", "steel glasses"),
        (r"kettle\b", "aluminium kettle"),
    ]
    for pat, repl in replacements:
        out = re.sub(pat, repl, out, flags=re.I)
    if "does not sit until" in text.lower():
        out += f" He waits for {mother}'s nod before taking a seat — baithak etiquette."
    return out


def _adapt_dialogue(text: str, speaker: str, culture: dict, name_map: dict, culture_id: str = "majhi") -> str:
    t = " ".join(text.split())
    rules = [
        (r"You came back late\. You always do this when something is wrong\.",
         "Tu late aa gya, puttar. Jadon kujh gal hundi ae, tu aidaan hi ghumda ae."),
        (r"Nothing is wrong\. I just needed air\.",
         "Kujh gal nahi, Bebe. Saah lain nu bahar aaya si."),
        (r"That letter has been in your pocket for two days\. Either open it or give it to her\.",
         "Oh chiTThi do din to pocket vich pae. Ja khol, ja Bebe nu de de."),
        (r"If it is from my brother, it is a family matter\. Do not hide family matters from me\.",
         "Je mere veer di chiTThi ae te eh ghar di gal ae. Ghar di gal merethon lukai nahi jaandi."),
        (r"You look like a man who lost a bet and then lost the walk home\.",
         "Aidaan lagda ae jaan shart haar ke rasta vi haar aaya hovein, yaar."),
        (r"My uncle wrote\. He wants me to take the shop\. Mother still thinks I am studying\.",
         "Mama Jagtar ne likheya ae. Ohnu shop chahidi ae mere kolon. Bebe hun vi samajhdi ae main padhda peaa haan."),
        (r"You told her you had one year left\.",
         "Tainu ohnau dassiya si ikk saal baaki ae."),
        (r"I can hear you\. I am not a guest in my own kitchen\.",
         "Main sunn rahi haan. Apni rasoi vich main koi parai nahi."),
        (r"Sit\. Drink\. Then tell me the truth, not the version you prepared for strangers\.",
         "Beh ja. Chai pee le. Phir sach dass, oh gal nahi jo tu bazaar vaaste tyaar karke rakhi ae."),
        (r"After work\. I will tell you after work\.",
         "Kam ton baad, Bebe. Main dasanga kam ton baad."),
        (r"After work is how lies grow old\.",
         "Kam ton baad di gal naal jhooth buddha ho janda ae."),
        (r"If you take the shop, you stay\. If you stay, you become the man she already introduced to the neighbours\.",
         "Je shop le li, tu pind vich rehna. Te je rehana, oh bande banjna jehda Bebe ne paise nu pehlan hi dass chhaddiya ae."),
        (r"If I refuse, she will think I am ashamed of her brother's work\.",
         "Je na kar ditta, Bebe kahegi main Mama de kam ton sharmaunda haan."),
        (r"Then do not refuse in the street\. Go home and let her see your face when you say it\.",
         "Phir gall gali vich na kar. Ghar ja, Bebe tere moonh te vece je tu gall karein."),
        (r"Your sister already knows\. Your mother almost knows\. The only person still pretending is you\.",
         "Simran jaandi ae. Bebe lagbhag jaandi ae. Naatak sirf tu karan peaa ae."),
        (r"I will go home before evening\. I will not bring a stranger's courage with me\.",
         "Shaam ton pehlan ghar jaanga. Kise paraye di himmat chukk ke nahi avanga."),
        (r"Uncle asked me to leave the course and take the shop\. I hid the letter because I was afraid of disappointing you\.",
         "Mama ne course chhadd ke kiryana sambhalan nu keha ae. ChiTThi is vaaste lukai kyunki mainu darr si tuhanu niiraan na kar deaan."),
        (r"I can survive disappointment\. I cannot survive being the last to know\.",
         "Niiraan te main seh laini aan, puttar. Par ghar vich aakhri jaanan vaali nahi ban sakdi."),
        (r"We would have sat with you\. That is the whole point of this house\.",
         "Assi tere naal behnde. Eh kothi da matlab hi eh ae."),
        (r"I am sorry\. I am still not sure I want the shop\. I am sure I should have said so\.",
         "Maaf kar de, Bebe. Shop baare hun vi pakka nahi. Pakka eh ae ke pehlan dassna chahida si."),
        (r"Then we will read it together\. After that, you will tell me what you want, not what you think I can bear\.",
         "Phir assaN ikkThhe paRhange. Us ton baad tu oh dass jehda tainu chahida ae, oh nahi jehda tainu lagda ae main seh sakdi haan."),
    ]
    if culture_id != "majhi":
        mother = "Maa" if culture_id == "malwai" else "Mother"
        out = t
        out = re.sub(r"\bMother\b", mother, out)
        out = re.sub(r"\buncle\b", "Mama", out, flags=re.I)
        names = culture.get("names", {})
        for src, row in names.items():
            out = re.sub(rf"\b{src.title()}\b", row["adapted_name"].split()[0], out)
        return out
    for pat, repl in rules:
        if re.search(pat, t, flags=re.I):
            return repl
    out = t
    out = re.sub(r"\bMother\b", "Bebe", out)
    out = re.sub(r"\buncle\b", "Mama", out, flags=re.I)
    out = re.sub(r"\bletter\b", "chiTThi", out, flags=re.I)
    return out


def _dialogue_reason(speaker: str, source: str) -> str:
    if "shop" in source.lower():
        return "Work and izzat are named as Mama's kiryana, not a generic shop."
    if "kitchen" in source.lower():
        return "Rasoi is the authority space; Bebe refuses guest status."
    if "street" in source.lower() or "neighbours" in source.lower():
        return "Public refusal would travel through the pind; Friend sends him home."
    if speaker.lower() == "mother":
        return "Kinship address and dignity (izzat) replace generic parental scolding."
    return "Majhi rhythm, kinship, and household space — not word-for-word English."


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = w if not cur else f"{cur} {w}"
        if len(trial) > width:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def _to_gurmukhi(roman: str) -> str:
    out = roman
    for src, dst in sorted(GURMUKHI_MAP.items(), key=lambda kv: len(kv[0]), reverse=True):
        out = out.replace(src, dst)
        out = out.replace(src.upper(), dst)
    return (
        "ਨੋਟ: Full literary Gurmukhi would be written by a native Majhi reviewer. "
        "This track transliterates key kinship and place terms so the production pack "
        "never mixes an unrelated script's identity.\n\n"
        + out
    )
