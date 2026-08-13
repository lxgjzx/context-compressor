# Compression Strategies

Deep library for the Context Compressor skill. Read the strategy you need; SKILL.md covers the 5-step workflow.

## Contents
1. Choosing a strategy
2. Rolling window
3. Map-reduce hierarchical summarization
4. State block (facts that must survive)
5. Token budget allocation
6. File-blob compression
7. Noise removal patterns
8. Anti-patterns
9. Worked example

## 1. Choosing a strategy

| Situation | Strategy |
|---|---|
| Context ~70–90% full, short session | Prune (drop DROP items only) |
| Long session, heavy history | Rolling window |
| Fact-heavy (many decisions/TODOs) | State block |
| Huge pasted files / tool dumps | File-blob compression |
| Very long transcript (>10k lines) | Map-reduce summarization |
| Repetitive logs | Dedup + strip + truncate |

## 2. Rolling window

Keep the last 10–15 turns verbatim. Everything older becomes one "History summary" block, itself re-summarized on each compression round (recursive: summary of summary + new events).

Rules:
- Never summarize the active turn or the user's latest message.
- Each round, merge the previous summary into the new one — do not discard it.
- Cap the history summary at ~2–4k tokens.

Example shape:

```
[History summary v3 — turns 1–80]
[verbatim turns 81–95]
```

## 3. Map-reduce hierarchical summarization

For transcripts too long to summarize in one pass:

1. Split into blocks of ~100–200 turns (or ~10k tokens each).
2. Summarize each block independently (map).
3. Summarize the block summaries (reduce).
4. Repeat reduce until one summary fits the budget.

Preserve: decisions, constraints, TODOs, paths, errors. Drop: prose, tool chatter, repeated attempts.

## 4. State block

A compact always-keep block. Template:

```
## Session state
GOAL: <one line>
STEP: <current step / next action>
CONSTRAINTS: <stack, format, style, budget>
DECISIONS:
- <decision> (why)
TODOS:
- [ ] <todo> — next: <action>
FILES: <paths and roles>
QUIRKS: <env discoveries>
```

Refresh it every compression round; keep it in the compressed output.

## 5. Token budget allocation

For a 200k window, a sane post-compression split:

- System + skills: ~10–20%
- Working state (state block + current step): ~15–25%
- History summary: ~10–20%
- Verbatim recent turns: ~30–40%
- Headroom: ~15%

For smaller windows, shrink **history** first — never the current working state:

| Window | Verbatim recent turns | History summary cap |
|---|---|---|
| 200k | last 10–15 turns | ~10–20k tokens |
| 128k | last 8–12 turns | ~6–10k tokens |
| 32k | last 5–8 turns | ~2–4k tokens |

## 6. File-blob compression

Large file contents pasted into chat: replace with

`<path> — <purpose> — key symbols: <names> — <git sha / diff summary>`

Keep exact signatures for anything the next step will touch.

## 7. Noise removal patterns

- Consecutive duplicate lines → `dedup`
- ANSI codes → `strip`
- Separator lines / lone timestamps → `strip`
- Base64 blobs ≥120 chars that are ≥85% base64 → `strip`
- Repeated identical tool outputs → `dedup`
- Lines that are only `ok` / `done` / `exit code 0` → `strip`

## 8. Anti-patterns

- Paraphrasing identifiers/commands — never; keep them exact.
- Summarizing before a phase ends — the summary misses the outcome.
- Dropping error messages — the next failure needs the exact string.
- "discussed X" summaries — useless; write the outcome.
- Compressing the user's active work — wait for a natural pause.
- Rewriting repo files during compression — compression targets the conversation, not the codebase (unless the user asks).

## 9. Worked example

**Before** (transcript, ~90k tokens):

```
User: build a scraper for site X
Assistant: [long plan]
User: ok, use python
Assistant: [20 tool calls, installs packages, debug loop, 3 failed retries]
User: now also export to csv
Assistant: [15 tool calls, final code in scraper.py]
User: add retry logic for 429s
Assistant: [12 tool calls, done]
```

**After** (~18k tokens):

```
## Session state
GOAL: scraper for site X + CSV export + 429 retry
STEP: retry logic just finished — next: user review / deploy
CONSTRAINTS: python, stdlib+requests, csv output
DECISIONS:
- requests + sleep-based 429 retry, max 5 attempts (no backoff lib)
- csv written via csv.writer, UTF-8 BOM
TODOS:
- [ ] run final end-to-end test on 500 rows
FILES: scraper.py (entry), requirements.txt
QUIRKS: site X blocks >10 req/min → keep delay 7s

[History summary — turns 1–80]
[verbatim turns 81–95]
```
