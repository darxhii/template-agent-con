---
name: research
description: >
  Web research playbook for the reporter subagent: query design, parallel
  search strategy, source hygiene, and how to turn search_web results into
  a grounded draft. Use for every topic or news research task.
---

# Web research (reporter)

Use this skill together with the **`search_web`** tool. **Never** present facts from model memory when search can answer; **never** invent URLs or outlets.

## Query planning — **breadth first (do not under-fetch)**

Goal: **cover the specific topic thoroughly** so the draft and RAG are not missing major angles. Under-fetching **directly hurts** fact-checker and editor quality.

Before calling `search_web`, define:

1. **Core topic** — the user’s entity, conflict, product, or question in 2–8 words.
2. **Angles** — you need **at least 5 distinct queries** for a normal topic (6–7 is better). Each must explore a **different** facet, not synonyms:
   - **Breaking / latest:** `{topic} latest news`, `{topic}` + current year if relevant
   - **Background / explainer:** `{topic} explained`, `{topic} what happened`, `{topic} timeline`
   - **Stakeholders / actors:** key people, organizations, or countries + `{topic}`
   - **Official / primary:** `{topic} official statement`, site:gov or major outlet if appropriate
   - **Regional or secondary angles:** neighbors, economy, humanitarian, legal — only if relevant to the user ask
3. **Batching:** Prefer **one** `search_web` call with **`queries` as a list of 5–8 strings** (parallel). If you **must** run a second batch (thin results or new sub-questions), run another `search_web` and then **append** to RAG (see below) — do **not** drop the first batch.

## `search_web` parameters

- **`queries`:** non-empty `list[str]`; **minimum 5** strings for a standard topic unless the user asked an extremely narrow single fact.
- **`max_results`:** use **`8`** per query for standard topic research (retrieve enough snippets). Use **5–6** only for a deliberately minimal or follow-up pass.

## Using results

- **Deduplicate by URL** mentally when reading tool output — the tool may already dedupe; still avoid repeating the same story twice in prose.
- **Prefer** recognizable outlets, official pages, or major wires when snippets agree; **flag** single anonymous or low-context hits as weaker support.
- **Conflicting snippets:** report both sides briefly and attribute (“Source A reports …; Source B indicates …”) — do not pick a winner without evidence in the results.
- **Map claims to evidence:** each non-obvious factual sentence in your summary should be traceable to a **title/snippet/url** you saw.

## Source list hygiene

- Every **Sources** line: `[Title or site name](https://url)` using the tool’s **`url`** field.
- **Do not** list a source you did not meaningfully use in the narrative.
- **Do not** fabricate or “fix” URLs.

## When results are thin

- Say so explicitly; widen queries once (alternate keywords, adjacent entities) if the topic is clear.
- If still thin after a second batch, deliver a short brief labeled **limited evidence** and avoid strong conclusions.

## RAG indexing — **save everything that backs the topic** (mandatory when `Story-ID` exists)

The orchestrator includes **`Story-ID: <id>`** in your task. Use that exact string as **`story_id`**.

**You must not return** until **all** successful `search_web` material for this topic is **indexed**, or you document a hard tool failure. Otherwise downstream agents lose retrieval and **quality is compromised**.

### Option A (preferred): one big search, one ingest

1. Run **one** `search_web` with **5–8 queries** and **`max_results` 8**.
2. Call **`research_rag_ingest_search_results`** with `replace_existing=true` (default):
   - **`story_id`:** `Story-ID`
   - **`search_web_result_json`:** JSON string of the **entire** tool return (including **every** item in `results`).

### Option B: multiple search rounds without losing data

1. First batch: ingest with **`replace_existing=true`** (starts a clean store for this story).
2. **Further** batches: ingest with **`replace_existing=false`** (**append**) so **previous chunks stay**.

### Merge alternative

If you manually merge `results` from several calls into **one** list inside a single JSON object, use **one** ingest with **`replace_existing=true`**.

Downstream **editor** and **fact-checker** use **`research_rag_query`**. They can only retrieve what you stored — **incomplete ingest = incomplete verification**.

## Handoff to downstream agents

Your draft is input to **fact-checker** and **editor**. Keep claims **discrete** (clear sentences or bullets) so claims are easy to audit. Leave **Sources** rich with links so fact-checker and editor can reuse URLs.
