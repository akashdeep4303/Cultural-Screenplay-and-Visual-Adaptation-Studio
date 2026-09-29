from __future__ import annotations

import argparse
from pathlib import Path

from app.engine.models import CultureChoice
from app.engine.pipeline import (
    approve_extraction,
    approve_plan_and_costumes,
    export_pack,
    generate_visuals,
    new_project,
    rewrite,
)
from app.engine.store import ProjectStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Cultural Screenplay Adaptation Studio CLI")
    parser.add_argument("--screenplay", required=True)
    parser.add_argument("--culture", default="majhi")
    parser.add_argument("--setting", default="rural", choices=["rural", "urban"])
    parser.add_argument("--script", default="roman", choices=["roman", "gurmukhi"])
    parser.add_argument("--region", default="")
    parser.add_argument("--out", default="sample_output")
    parser.add_argument("--auto-approve", action="store_true")
    args = parser.parse_args()

    text = Path(args.screenplay).read_text(encoding="utf-8")
    from app.engine.cultures import load_culture

    pack = load_culture(args.culture)
    choice = CultureChoice(
        culture_id=args.culture,
        dialect=pack["dialect"],
        region=args.region or pack["region"],
        setting=args.setting,
        script=args.script,
    )
    state = new_project(text, choice, filename=Path(args.screenplay).name)
    if args.auto_approve:
        approve_extraction(state)
        approve_plan_and_costumes(state)
        rewrite(state)
        out = Path(args.out)
        generate_visuals(state, out)
        export_pack(state, out)
        store = ProjectStore()
        store.save(state)
        print(f"project_id={state.project_id}")
        print(f"wrote {out.resolve()}")
        print(f"review_items={len(state.adaptation_plan.uncertain_choices) if state.adaptation_plan else 0}")
    else:
        print("Created extraction. Re-run with --auto-approve or use the web app to approve gates.")
        print(f"scenes={len(state.scenes)} characters={len(state.characters)}")


if __name__ == "__main__":
    main()
