# Live demonstration script (6–8 minutes)

Use a fresh browser tab at [http://127.0.0.1:8000](http://127.0.0.1:8000). Speak the **Say** lines; do the **Do** actions. Do not generate visuals until the contradiction beat is finished.

```bash
uvicorn app.main:app --reload --port 8000
```

---

## 0. Setup (20 seconds)

**Do:** Click **Load sample screenplay**. Leave culture on **Majhi**, setting **Rural**, script **Roman Punjabi**.

**Say:** “Source is culturally neutral English. The job is not translation. It is an exact Majhi household in rural Majha, with canonical IDs that survive every later rewrite and every picture.”

Click **Extract scenes**.

---

## 1. One character: source mention → canonical record → adapted identity → consistent pictures

**Do:** On the character table, point at `CHAR_ADAM`.

**Say:** “The screenplay says ADAM. Extraction creates one record: `CHAR_ADAM`. The plan adapts him to **Jaswant Singh**. Uncle is an off-screen alias, not a second body. If the parser also invented ‘Elder Son’, that is a duplicate identity, not a new person.”

**Do:** Click **Show duplicate: Elder Son**. The table now has `CHAR_ELDER_SON`. Fill merge boxes Adam / Elder Son, click **Merge**. `CHAR_ELDER_SON` disappears; `Elder Son` is an alias on `CHAR_ADAM`.

**Say:** “Canonical ID did not change. Later visuals lock to `CHAR_ADAM`, so the face, parna, faded jacket, and kara stay the same in the bible and in every scene he enters.”

Return to this plate after generation: `CHAR_ADAM` then SC01–SC04. Same navy parna, same jacket, same gold kara on the right wrist.

---

## 2. One costume / prop across multiple scenes (the jacketed letter)

**Do:** Open **Approval**. Point at `COST_ADAM_01` — scenes SC01, SC02, SC03, SC04. Then open continuity on Extraction: carrying `PROP_LETTER`.

**Say:** “One costume variant. No story reason to change clothes, so the jacket is reused. The letter is the audit prop: hand in the aangan, pocket in the rasoi and on the mandi road, table in the baithak. If a picture showed a new shirt in scene 3, that would be a continuity break, not a style choice.”

After generation, walk SC01 (letter in hand) → SC02 (pocket) → SC03 (still pocket, not opened on the street) → SC04 (chiTThi on the low table). Jacket colour and cut do not change.

---

## 3. One cultural adaptation that is more than translation

**Do:** On the plan, read **D03 verbal texture** and **D04 non-verbal**. Then **Approve plan and costumes**, **Rewrite screenplay**, compare source vs adapted.

**Say:** “Mother is not translated as ‘Maa’ here. Majhi rural address is **Bebe**. The shop is **Mama Jagtar’s kiryana**, because the stake is the mother’s brother’s izzat, not a generic career plot. Scene 3 does not let him refuse in the street — Friend sends him home so Bebe can see his face. That is blocking and kinship, not a glossary swap. Malwai would use Maa and different names in a separate project. Those strings must never appear in this one.”

Point at one line: source “Nothing is wrong” → adapted “Kujh gal nahi, Bebe.”

---

## 4. One contradiction caught before visual generation

**Do:** Go back to Extraction. Click **Detect contradiction: letter vanishes in SC04**. Continuity on SC04 turns red. Click **Generate visual pack** without fixing it.

**Say:** “Scene 4 now has Adam empty-handed and no letter. Continuity already knew the letter was in his pocket. Generation is refused until that is resolved. We do not paint a lie and patch it in review.”

**Do:** Click **Extract scenes** again (reload sample if needed) to restore a clean project. Approve extraction, approve plan, rewrite, then generate.

**Say:** “Gates: extraction, cultural plan, costumes, and a clean continuity walk. Only then the renderer runs.”

---

## 5. User corrects an extraction or cultural choice; only affected outputs regenerate

**Do:** On Visuals, use **Correct and regenerate**:

| Field | Demo A (costume) | Demo B (culture, if time) |
| --- | --- | --- |
| Kind | Costume | Cultural plan |
| ID | `COST_ADAM_01` | `D03` |
| Field | `colours` | `adapted` |
| Value | `mustard, navy, dust tan` | keep Bebe; or show why Maa would be wrong |

Click **Apply + regenerate affected**.

**Say:** “The patch writes `CHAR_ADAM`, `COST_ADAM_01`, and the scenes he stands in. Sister’s costume plate is not redrawn. That is the point of canonical IDs: a human correction is cheap and local.”

If you used mustard, point at Jaswant’s kurta shifting from off-white to mustard in his bible and in the four keyframes, while Simran’s mint kameez is unchanged.

---

## 6. How assistants were used, what they got wrong, how we verified

**Say:** “A coding assistant drafted the parser, Majhi lines, and the first SVG geometry. Three failures were caught in review, not by the model congratulating itself.”

1. **Parser:** it treated `SCENE 1` as a heading, which would have duplicated scenes. We ignore number-only markers. Verified by four `SC0*` IDs in tests and in this table.
2. **Culture leak:** one dialogue table would have put **Bebe** into Malwai. Adaptation now branches on `culture_id`. Verified by `test_culture_memory_does_not_leak`.
3. **Pretty pictures too early:** an assistant will happily render before approval. The pipeline raises if gates are closed or the letter is missing. You just saw the 409-style block.
4. **Majhi evidence:** we did not ask a public LLM what rural Amritsar sounds like. Culture packs are local JSON. Uncertain items stay on the plan (Amritsar city vs pind slang; kinship tone after conflict).

**Say:** “Verification is pytest, this click-path, and reading the change log against the source beat: same speaker, same story move, no new plot.”

Close on Export: `adapted_screenplay.pdf`, `continuity_report.pdf`, SVG pack with prompts and seeds so a hosted image model can replace the SVG renderer without changing IDs.

---

## Timing cheat-sheet

| Beat | Clock |
| --- | --- |
| Setup + extract | 0:00–0:40 |
| Character + merge | 0:40–2:00 |
| Costume / letter path | 2:00–3:00 |
| Bebe / baithak / no street refusal | 3:00–4:20 |
| Contradiction block | 4:20–5:20 |
| Correct + partial regen | 5:20–6:20 |
| Assistant errors + tests | 6:20–7:30 |
| Export pack | 7:30–8:00 |
