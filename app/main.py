from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.engine.cultures import available_cultures, load_culture
from app.engine.models import CultureChoice
from app.engine.pipeline import (
    PipelineError,
    apply_correction,
    approve_extraction,
    approve_plan_and_costumes,
    export_pack,
    generate_visuals,
    inject_duplicate_alias,
    inject_letter_contradiction,
    merge_by_source,
    new_project,
    regenerate_affected,
    retry_one_visual,
    rewrite,
)
from app.engine.store import ProjectStore

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
SAMPLE = ROOT / "data" / "sample_screenplay.txt"

app = FastAPI(title="Cultural Screenplay Adaptation Studio", version="1.0.0")
store = ProjectStore()


class CultureBody(BaseModel):
    culture_id: str = "majhi"
    setting: str = "rural"
    script: str = "roman"
    region: str = ""
    dialect: str = ""


class MergeBody(BaseModel):
    keep: str
    drop: str


class PatchBody(BaseModel):
    kind: str
    target_id: str
    field: str
    value: str
    regenerate: bool = True


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/cultures")
def cultures() -> list[dict]:
    return available_cultures()


@app.get("/api/sample")
def sample() -> dict:
    return {"filename": "sample_screenplay.txt", "text": SAMPLE.read_text(encoding="utf-8")}


@app.post("/api/projects")
async def create_project(
    culture_id: str = Form("majhi"),
    setting: str = Form("rural"),
    script: str = Form("roman"),
    region: str = Form(""),
    text: str = Form(""),
    file: UploadFile | None = File(None),
) -> dict:
    filename = "pasted.txt"
    if file is not None:
        filename = file.filename or filename
        raw = await file.read()
        text = raw.decode("utf-8", errors="replace")
    if not text.strip():
        raise HTTPException(400, "Paste or upload a screenplay.")
    pack = load_culture(culture_id)
    choice = CultureChoice(
        culture_id=culture_id,
        dialect=pack["dialect"],
        region=region or pack["region"],
        setting=setting,
        script=script,
    )
    state = new_project(text, choice, filename=filename)
    store.save(state)
    return _public(state)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict:
    return _public(_load(project_id))


@app.post("/api/projects/{project_id}/merge")
def merge(project_id: str, body: MergeBody) -> dict:
    state = _load(project_id)
    merge_by_source(state, body.keep, body.drop)
    store.save(state)
    return _public(state)


@app.post("/api/projects/{project_id}/approve-extraction")
def approve_ext(project_id: str) -> dict:
    state = approve_extraction(_load(project_id))
    store.save(state)
    return _public(state)


@app.post("/api/projects/{project_id}/approve-plan")
def approve_plan(project_id: str) -> dict:
    state = approve_plan_and_costumes(_load(project_id))
    store.save(state)
    return _public(state)


@app.post("/api/projects/{project_id}/adapt")
def adapt(project_id: str) -> dict:
    state = rewrite(_load(project_id))
    store.save(state)
    return _public(state)


@app.post("/api/projects/{project_id}/generate")
def generate(project_id: str) -> dict:
    state = _load(project_id)
    out = store.artifacts_dir(project_id)
    try:
        generate_visuals(state, out)
    except PipelineError as exc:
        raise HTTPException(409, str(exc)) from exc
    export_pack(state, out)
    store.save(state)
    return _public(state)


@app.post("/api/projects/{project_id}/assets/{asset_id}/retry")
def retry(project_id: str, asset_id: str) -> dict:
    state = _load(project_id)
    try:
        retry_one_visual(state, asset_id, store.artifacts_dir(project_id))
    except PipelineError as exc:
        raise HTTPException(404, str(exc)) from exc
    store.save(state)
    return _public(state)


@app.post("/api/projects/{project_id}/demo/duplicate-alias")
def demo_duplicate(project_id: str) -> dict:
    state = inject_duplicate_alias(_load(project_id))
    store.save(state)
    return _public(state)


@app.post("/api/projects/{project_id}/demo/break-letter")
def demo_break_letter(project_id: str) -> dict:
    state = inject_letter_contradiction(_load(project_id))
    store.save(state)
    return _public(state)


@app.post("/api/projects/{project_id}/correct")
def correct(project_id: str, body: PatchBody) -> dict:
    state = _load(project_id)
    try:
        affected = apply_correction(state, body.kind, body.target_id, body.field, body.value)
        if body.kind in {"character", "plan"}:
            rewrite(state)
        if body.regenerate and state.visuals:
            regenerate_affected(state, store.artifacts_dir(project_id), affected)
            export_pack(state, store.artifacts_dir(project_id))
    except (PipelineError, StopIteration) as exc:
        raise HTTPException(400, str(exc)) from exc
    store.save(state)
    payload = _public(state)
    payload["affected_ids"] = sorted(affected)
    return payload


@app.get("/api/projects/{project_id}/files/{name}")
def download(project_id: str, name: str):
    allowed = {
        "adapted_screenplay.pdf",
        "adapted_screenplay.txt",
        "continuity_report.pdf",
        "continuity_report.md",
        "scene_breakdown.json",
        "project_state.json",
    }
    if name not in allowed:
        raise HTTPException(404, "Unknown export")
    path = store.artifacts_dir(project_id) / name
    if not path.exists():
        raise HTTPException(404, "Export not generated yet")
    return FileResponse(path)


@app.get("/api/projects/{project_id}/svg/{kind}/{filename}")
def svg(project_id: str, kind: str, filename: str):
    if kind not in {"character_bible", "costume_bible", "scene_keyframes"}:
        raise HTTPException(404)
    path = store.artifacts_dir(project_id) / kind / filename
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/svg+xml")


def _load(project_id: str):
    try:
        return store.get(project_id)
    except KeyError as exc:
        raise HTTPException(404, "Unknown project") from exc


def _public(state) -> dict:
    return {
        "project_id": state.project_id,
        "culture": state.culture.model_dump(),
        "extraction_problems": state.extraction_problems,
        "scenes": [s.model_dump() for s in state.scenes],
        "characters": [c.model_dump() for c in state.characters],
        "locations": [e.model_dump() for e in state.locations],
        "props": [e.model_dump() for e in state.props],
        "costumes": [c.model_dump() for c in state.costumes],
        "continuity": [c.model_dump() for c in state.continuity],
        "adaptation_plan": state.adaptation_plan.model_dump() if state.adaptation_plan else None,
        "adapted_screenplay": state.adapted_screenplay,
        "change_log": state.change_log,
        "visuals": [v.model_dump() for v in state.visuals],
        "extraction_approved": state.extraction_approved,
        "costumes_approved": state.costumes_approved,
        "human_notes": state.human_notes,
        "plan_approved": bool(state.adaptation_plan and state.adaptation_plan.approved),
        "gates": {
            "can_generate": bool(
                state.extraction_approved
                and state.costumes_approved
                and state.adaptation_plan
                and state.adaptation_plan.approved
                and not any(s.continuity_warnings for s in state.scenes)
            )
        },
    }


app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")
