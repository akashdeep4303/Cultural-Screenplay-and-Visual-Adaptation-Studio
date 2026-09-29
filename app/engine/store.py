from __future__ import annotations

import json
from pathlib import Path

from .models import ProjectState

ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "projects"


class ProjectStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.memory: dict[str, ProjectState] = {}

    def save(self, state: ProjectState) -> None:
        self.memory[state.project_id] = state
        path = self.root / f"{state.project_id}.json"
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def get(self, project_id: str) -> ProjectState:
        if project_id in self.memory:
            return self.memory[project_id]
        path = self.root / f"{project_id}.json"
        if not path.exists():
            raise KeyError(project_id)
        state = ProjectState.model_validate_json(path.read_text(encoding="utf-8"))
        self.memory[project_id] = state
        return state

    def artifacts_dir(self, project_id: str) -> Path:
        d = self.root / project_id
        d.mkdir(parents=True, exist_ok=True)
        return d
