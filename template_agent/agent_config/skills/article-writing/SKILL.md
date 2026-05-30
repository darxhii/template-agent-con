---
name: article-writing
description: >
  News-style article structure, headline and lead craft, analysis vs
  reporting boundaries, attribution, and Markdown output conventions for
  the editor subagent. Use when turning a verified draft into the final
  user-facing article.
---

# Article writing (editor)

Apply this after **fact-check** instructions are satisfied. You **report and synthesize** what you were given — **no new facts**, no **`search_web`**.

If the task includes **`Story-ID:`**, you may call **`research_rag_query`** with that id to retrieve **stored research excerpts** (e.g. “budget vote city council”, “timeline explosion”) to tighten attribution or fill **listener-aware** detail — still **no new live search** and **no facts** beyond what those chunks + draft + fact-check support.

## Voice and tone

- **Wire-service neutral:** third person; no “I / we” unless quoting.
- **Attribute:** “according to …”, “X reported …”, “officials said …” when the draft or fact-check supplies that chain.
- **Hedge** per fact-check: **partially_supported** → “reports suggest”, “one outlet indicated”; **unverified** removed or framed as uncertainty; **contradicted** removed or “claims conflict.”

## Section order (Markdown)

Use this order unless the orchestrator asked for a **minimal brief** only.

### 1. Headline (`#`)

- **Specific and active:** name the main actors, event, or tension — not “An update on …” or “Summary”.
- **Accurate:** must not overstate what survived fact-check.
- **Length:** roughly 6–14 words; no clickbait question headlines unless the user asked for that style.

### 2. Sub-head / dek

- One line under `#`: *italics* or `## Sub-head` with a single clarifying sentence (the “why read this” line).
- Still **factual framing** only — no new data.

### 3. `## Lead`

- **One paragraph** (rarely two if needed for clarity).
- **Inverted pyramid:** **who, what, when, where** in the first sentence when possible; next sentences add most important **how / why** only from verified material.
- No throat-clearing (“In recent developments…”).

### 4. `## Analysis`

- **2–4 short paragraphs.** Interpret **meaning**, **stakes**, **trade-offs**, **what to watch** — all grounded in facts already in the draft or fact-check narrative.
- **Forbidden:** new numbers, new names, new events, or new URLs not in inputs.
- If the **fact-check score** or verdicts show weakness, reflect **uncertainty** honestly in this section.

### 5. `## Key developments`

- **Bullets:** one idea per bullet; parallel grammar where possible.
- Tight; no mini-essays.
- Align bullets with **verified** or properly hedged **partially_supported** claims only.

### 6. `## Editor’s note` (optional)

- Use **only** if large claims were removed or heavily softened. One paragraph: corroboration limits; neutral; no blame.

### 7. `## Sources`

- **Every** line a Markdown link: `[Title or outlet](https://url)`.
- Pull URLs from the reporter draft or fact-check **Evidence** column if missing in draft.
- Drop sources that only supported removed claims. **Never** bare titles when a URL exists in the materials.

## Micro-style

- Prefer **said** over **stated**; **reported** for second-hand information.
- **Dates:** use forms present in the draft; do not invent precise dates.
- **Numbers:** repeat only what passed fact-check; round only if the draft did.

## Quality check before you finish

- [ ] Every strong factual claim in Lead and Key developments traceable to inputs.
- [ ] Analysis adds **interpretation**, not **information**.
- [ ] Sources are all links where URLs exist.
- [ ] Headline matches the **strongest** true claim you kept, not the old draft’s hype.
