---
name: context-compressor
description: Compress agent conversation context, transcripts, and session notes to save tokens and prevent context-window overflow in long sessions. Use when the user asks to compress/compact context, save tokens or cost, shrink conversation history, summarize long sessions, 压缩上下文, 上下文压缩, 节省token, or when the session is long and context usage is high. Works across agent frameworks (Claude Code, Codex, Cursor, Windsurf, OpenSquilla, etc.).
triggers:
- 压缩上下文
- 上下文压缩
- 节省token
- save tokens
- compact context
- context compression
- compress context
- 省点token
---

# Context Compressor

Compress long agent sessions so work continues smoothly inside the context window while nothing important is lost. Works in any agent that reads Markdown and can run Python 3.

## When to compress

Act proactively — do not wait for the user:

- Estimated context usage ≥ 70% of the window (use `scripts/compress.py count` on transcripts/logs, or your runtime's usage indicator).
- Session passed ~30 turns, or a task phase just completed (feature shipped, bug fixed, review done) and a new phase starts.
- Before spawning a subagent, switching tasks, or reading a very large file into context.
- User explicitly asks (e.g., "压缩上下文 / save tokens / compact context / 省点token").

Do NOT compress mid-flow inside the user's active working block (e.g., while debugging a live failure). Wait for a natural pause.

## Workflow (5 steps)

1. **Inventory** — scan recent turns; tag each block KEEP / SUMMARIZE / DROP:
   - KEEP: active goal, current step, constraints, decisions, TODOs, file paths, commands, identifiers, exact error strings.
   - SUMMARIZE: completed work, resolved discussions, explained concepts whose outcome matters but prose does not.
   - DROP: failed retries, repeated tool output, boilerplate, long raw logs, greetings, dead ends.

2. **Choose strategy** (full library: `references/strategies.md`):
   - Small surplus → **prune** DROP items only.
   - Long session → **rolling window**: last ~10–15 turns verbatim, older turns summarized.
   - Fact-heavy session → **state block**: one dense block of decisions, open TODOs, paths, env quirks.
   - Pasted file blobs → replace with `path + purpose + key symbols + git sha / diff summary`.

3. **Mechanically compress** with `scripts/compress.py` (semantic summarization stays with you):
   ```bash
   python3 scripts/compress.py count transcript.md            # token estimate
   python3 scripts/compress.py report logs/*.md               # before/after table
   python3 scripts/compress.py truncate transcript.md --keep-tokens 4000 --dry-run   # token-budget mode (preferred)
   python3 scripts/compress.py truncate transcript.md --keep-head 20 --keep-tail 15 --dry-run
   python3 scripts/compress.py dedup notes.md
   python3 scripts/compress.py strip raw.md --dry-run
   ```
   Run with `--dry-run` first; drop it to write in place.

4. **Verify (mandatory)** — read the compressed result alone and answer: can a fresh agent continue this task using only this text? If any item in the "Never lose" checklist is missing, restore it.

5. **Report** — tell the user what was compressed and the estimated savings, e.g. `"~210k → ~28k tokens (−87%): dropped 2 failed retry loops, summarized 3 resolved discussions, kept all decisions + TODOs."`

## Never lose (mandatory checklist)

- Active goal and current workflow step.
- Hard constraints / preferences (stack, format, style, budget, tone).
- Decisions with one-line rationale; open TODOs with next action.
- Exact strings needed later: error messages, IDs, commands, paths, branch names.
- Environment quirks discovered (versions, port conflicts, workarounds).

## Summary quality rules

- Concrete over vague: `decided X = Y (because Z)` — never `discussed X`.
- Keep numbers, names, commands exact; never paraphrase identifiers.
- Dense bullet lines beat prose paragraphs.
- When in doubt, keep it.

## Compatibility

Markdown + Python 3 stdlib only; no network, no config files, no secrets. Ports to any agent — see `references/agents.md` for the installation map.
