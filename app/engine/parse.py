from __future__ import annotations

import re
from dataclasses import dataclass, field


SCENE_HEADING = re.compile(
    r"^(?:SCENE\s+(?P<num>\d+)\s*)?(?P<ie>INT|EXT|INT/?EXT|I/E)\.\s*(?P<rest>.+)$",
    re.IGNORECASE,
)
SPEAKER = re.compile(r"^[A-Z][A-Z0-9 .']{1,28}$")
SKIP_SPEAKERS = {"END", "FADE OUT", "FADE IN", "CUT TO", "THE END"}


@dataclass
class RawBeat:
    kind: str
    text: str
    speaker: str = ""


@dataclass
class RawScene:
    heading: str
    number: int
    int_ext: str
    location: str
    time: str
    beats: list[RawBeat] = field(default_factory=list)


def parse_screenplay(text: str) -> tuple[list[RawScene], list[str]]:
    problems: list[str] = []
    lines = text.replace("\r\n", "\n").split("\n")
    scenes: list[RawScene] = []
    current: RawScene | None = None
    pending_speaker: str | None = None
    scene_counter = 0
    dialogue_buf: list[str] = []

    def flush_dialogue() -> None:
        nonlocal pending_speaker, dialogue_buf
        if current is None or not pending_speaker:
            dialogue_buf = []
            pending_speaker = None
            return
        speech = " ".join(x.strip() for x in dialogue_buf if x.strip())
        if speech:
            current.beats.append(RawBeat("dialogue", speech, pending_speaker))
        dialogue_buf = []
        pending_speaker = None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            if pending_speaker:
                flush_dialogue()
            continue

        scene_num_only = re.match(r"^SCENE\s+(\d+)\s*$", stripped, re.I)
        if scene_num_only:
            scene_counter = int(scene_num_only.group(1)) - 1
            continue

        heading_match = SCENE_HEADING.match(stripped)
        if heading_match:
            flush_dialogue()
            ie_raw = heading_match.group("ie").upper()
            if "INT" in ie_raw and "EXT" in ie_raw:
                ie = "INT/EXT"
            elif "INT" in ie_raw:
                ie = "INT"
            else:
                ie = "EXT"
            rest = heading_match.group("rest")
            number = int(heading_match.group("num") or 0)

            location, time = _split_location_time(rest)
            scene_counter += 1
            number = number or scene_counter
            current = RawScene(
                heading=stripped,
                number=number,
                int_ext=ie,
                location=location,
                time=time,
            )
            scenes.append(current)
            continue

        if current is None:
            continue

        if pending_speaker:
            if SPEAKER.match(stripped) and stripped.upper() not in SKIP_SPEAKERS:
                flush_dialogue()
                pending_speaker = _speaker_name(stripped)
            else:
                dialogue_buf.append(stripped)
            continue

        if SPEAKER.match(stripped) and stripped.upper() not in SKIP_SPEAKERS:
            pending_speaker = _speaker_name(stripped)
            continue

        if stripped.upper() in SKIP_SPEAKERS or stripped.upper() == "END.":
            continue

        current.beats.append(RawBeat("action", stripped))

    flush_dialogue()
    if not scenes:
        problems.append("No INT/EXT scene headings were found. Check fountain-style headings.")
    for scene in scenes:
        if not any(b.kind == "dialogue" for b in scene.beats):
            problems.append(f"Scene {scene.number} has no dialogue.")
    return scenes, problems


def _speaker_name(text: str) -> str:
    return re.sub(r"\s*\(.*\)\s*", "", text).strip().title()


def _split_location_time(rest: str) -> tuple[str, str]:
    parts = [p.strip() for p in rest.split(" - ")]
    if len(parts) == 1:
        return parts[0].title(), ""
    return " - ".join(parts[:-1]).title(), parts[-1].title()
