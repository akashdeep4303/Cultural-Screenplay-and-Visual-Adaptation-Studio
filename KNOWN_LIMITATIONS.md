# Known limitations

Intentionally incomplete so the 48-hour MVP stays end-to-end rather than wide and broken.

- **DOCX/PDF upload** is not parsed natively; paste text or upload TXT.
- **Photoreal hosted images** are not called (privacy + no evaluator key). The SVG renderer is an illustrated production plate (not a camera still). Prompts and seeds are stored so a hosted model can replace the renderer without changing canonical IDs.
- **Gurmukhi** is a marked track (kinship and place terms), not a full literary translation. A native reviewer should still sit on the review queue.
- **Inline table editing** in the UI is limited; merge is supported, arbitrary cell edits are not a spreadsheet.
- **Urban Majhi** changes architecture strings more than the full Amritsar street lexicon.
- **Demo video** (`demo_video.mp4`) is not recorded in this folder; follow [DEMONSTRATION.md](DEMONSTRATION.md) and capture 6–8 minutes of the local app.
- **Second culture** is implemented as an isolated pack and tests, not as a dual-tab UI.
- Dialogue adaptation uses an evidence glossary plus patterns, not unbounded generation, so unseen lines get a light code-switch rather than fluent invention.
