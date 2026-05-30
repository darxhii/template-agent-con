---
name: fact-check-score
description: >
  Defines how to compute a single 0–100 fact-check score from verdict
  classifications after validation. Use when finishing a fact-check audit
  so the editor and user can see overall grounding quality.
---

# Fact-check score (0–100)

After you have assigned each reviewed claim exactly one status in the verdict table, compute **one** integer score from **0** to **100** using the rubric below. **Do not invent** counts — they must match the verdict table rows.

## Status → points (per claim)

Each claim contributes **claim points** according to its final status:

| Status | Claim points |
|--------|----------------|
| **verified** | 1.00 |
| **partially_supported** | 0.55 |
| **unverified** | 0.20 |
| **contradicted** | 0.00 |

## Formula

Let **N** = number of claims in the verdict table (one row per claim you audited).

Let **S** = sum of claim points for all **N** rows (using the table above).

**Fact-check score** = `round(100 × S / N)` — round to the nearest integer, then clamp to **[0, 100]**.

### Examples

- N=4, all **verified** → S=4 → score = **100**
- N=4, two **verified**, two **partially_supported** → S=2+1.1=3.1 → 100×3.1/4 = **78**
- N=5, one **contradicted**, four **verified** → S=4 → **80**
- N=10, mix: 5V + 3P + 1U + 1C → S = 5 + 1.65 + 0.2 + 0 = 6.85 → **69**

## Bands (interpretation text)

Use this wording (or close paraphrase) for the **Interpretation** line after the score:

| Score | Label | Suggested one-line interpretation |
|-------|--------|-----------------------------------|
| 85–100 | **Strong** | Most or all checked claims are well supported by search evidence. |
| 70–84 | **Good** | Generally grounded; several claims need hedging or stronger attribution. |
| 55–69 | **Mixed** | Material gaps or weak support on multiple claims; substantive edits expected. |
| 40–54 | **Weak** | Many claims poorly supported or contested; treat draft as unreliable without heavy revision. |
| 0–39 | **Poor** | Widespread unverified or contradicted claims; not suitable as factual reporting without major rework. |

## Edge cases

| Situation | Score |
|-----------|--------|
| **N = 0** (no checkable factual claims reviewed) | Use **N/A** — explain “No discrete factual claims were audited.” Do not assign a numeric score. |
| **`search_web` failed** for the whole run (no usable verification) | **N/A** — explain the failure; do not fabricate a numeric score. |
| **Mixed success** (some queries failed) | Still score rows you could classify; add a note under **Residual risks** that verification was incomplete. |

## Required output snippet

In the fact-check report, include a section **## Fact-check score** with:

1. **`Score: XX/100`** (or **`Score: N/A`**) on the first line.
2. **`Interpretation:`** one sentence using the band table.
3. **`Breakdown:`** counts **V** / **P** / **U** / **C** (verified / partially_supported / unverified / contradicted) and **N** total.
4. **`Calculation:`** show `S = (V×1 + P×0.55 + U×0.2 + C×0) = …` then `round(100 × S / N) = XX`.

This keeps the score **auditable** from the verdict table.
