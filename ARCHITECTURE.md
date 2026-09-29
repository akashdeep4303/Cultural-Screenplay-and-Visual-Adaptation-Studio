# Architecture

## Sequence

1. **Parse** fountain-style `INT.` / `EXT.` headings. Standalone `SCENE N` lines are numbering only.
2. **Extract** scenes, speakers, action, props, locations.
3. **Normalize** aliases into `CHAR_*`, `LOC_*`, `PROP_*`, `COST_*_01`.
4. **Continuity** walks scenes in order and updates wearing, carrying, knowledge, emotion. The letter is the audit prop: pocket → still pocket → table.
5. **Plan** writes cultural decisions (names, work, kinship, gesture, world) before any rewrite.
6. **Human gates** approve extraction, then plan+costumes.
7. **Adapt** rewrites dialogue and blocking from the approved plan. Independent of the SVG renderer.
8. **Verify** duplicate IDs, costume changes without reason, missing letter, culture leakage (tested Majhi vs Malwai).
9. **Generate** deterministic SVG plates plus a reproducible prompt/seed. Retry is per asset.
10. **Export** PDF, JSON, SVG.

## Memory

Each project is an isolated `ProjectState` (JSON on disk under `data/projects/`). Two cultures never share canonical IDs or prompt context. Costume `_01` is reused until a scene states a change.

## Verification vs generation

The translator/adapter does not approve itself. Continuity and approval checks run in Python and can raise `PipelineError` (HTTP 409) to block visuals.

## Failure recovery

- Missing headings → extraction problem list, no silent scene invention.
- Model/provider: mock path is the default; no evaluator API key.
- One SVG retry does not re-extract or re-adapt.
- Contract for a second culture is a new project, not a flag on the first.

## Trust boundaries

- Culture JSON packs are the only authoritative cultural evidence (not the public web).
- User approvals are required before visuals.
- Uncertain items stay on the plan (`uncertain_choices`) instead of being invented as fact.
- Image “generation” here is a studio plate renderer; prompts are included so a hosted image model can be swapped in without changing IDs.
