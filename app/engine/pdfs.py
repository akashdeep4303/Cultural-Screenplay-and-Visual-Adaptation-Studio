from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Preformatted


def write_pdf(path: Path, title: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm)
    styles = getSampleStyleSheet()
    story = [Paragraph(title.replace("&", "&amp;"), styles["Title"]), Spacer(1, 8)]
    safe = body.replace("\t", "    ")
    story.append(Preformatted(safe, styles["Code"]))
    doc.build(story)
