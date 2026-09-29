# AI usage log

This repository was implemented with Cursor Grok 4.6 in one session after reading all three assignment PDFs.

## What the assistant did

- Compared the three briefs and selected the cultural studio (web MVP, exact dialect, continuity, visual pack).
- Wrote the parser, canonical extractors, Majhi/Malwai packs, FastAPI app, SVG renderer, tests, and docs.
- Drafted Majhi dialogue. Every line was then checked against the source beat (same speaker, same story move, no new plot).
- First SVG pass was geometric (circles, rectangles). That look was rejected in review and replaced with a continuity-locked illustrated renderer (skin shading, garments, Majha locations, letter tracking).

## What was rejected or corrected

- Treating `SCENE 1` as an `EXT.` heading — that would have duplicated or mis-numbered scenes. Parser now ignores number-only markers.
- A single Majhi dialogue table applied to Malwai — that leaked `Bebe` into the second culture. Adaptation now branches on `culture_id`.
- Generating pretty images before approval — the pipeline raises if gates are closed.
- Using a public LLM as evidence for Majhi — culture packs are local JSON only.

## How output was verified

- `pytest` for extraction, alias merge, letter continuity, approval gate, culture isolation, and single-asset retry.
- CLI `--auto-approve` to materialise `sample_output/`.
- Browser pass of upload → extract → approve → adapt → generate → export when the app is running.
