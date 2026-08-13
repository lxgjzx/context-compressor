# Context Compressor

[![CI](https://github.com/lxgjzx/context-compressor/actions/workflows/ci.yml/badge.svg)](https://github.com/lxgjzx/context-compressor/actions/workflows/ci.yml)

A framework-agnostic skill for compressing agent conversation context, transcripts, and session notes — saving tokens and preventing context-window overflow in long-running sessions.

> 中文文档: [README.zh-CN.md](README.zh-CN.md)

Works with **Claude Code, Codex, Cursor, Windsurf, OpenSquilla**, and any agent that can read Markdown and run Python 3 (stdlib only).

## Why

Long agent sessions accumulate noise: retried commands, repeated tool output, ANSI escapes, base64 blobs, boilerplate, and resolved discussions. Context Compressor gives you:

- A clear **when-to-compress** policy (context ≥70% full, >30 turns, phase completed, before spawning subagents, …).
- A 5-step **workflow** — inventory → strategy → compress → verify → report.
- A **"never lose" checklist** — active goal, constraints, decisions, TODOs, exact error strings, env quirks.
- A **pure-stdlib Python tool** (`scripts/compress.py`) for the mechanical parts.

## Install

Copy the folder into your agent's skills/rules location:

| Agent | Path |
|---|---|
| Claude Code | `~/.claude/skills/context-compressor/` (personal) or `.claude/skills/context-compressor/` (project) |
| Codex | `.agents/skills/context-compressor/` (see `AGENTS.md`) |
| Cursor | `.cursor/rules/context-compressor.mdc` (or reference the folder) |
| Windsurf | `.windsurf/rules/context-compressor.md` |
| OpenSquilla | `skills/context-compressor/` (workspace) |

See `references/agents.md` for the full compatibility map and porting recipe.

## CLI usage

```bash
# estimate tokens
python3 scripts/compress.py count transcript.md
python3 scripts/compress.py report logs/*.md     # before/after table

# mechanical compression (add --dry-run to preview without writing)
python3 scripts/compress.py strip transcript.md
python3 scripts/compress.py dedup transcript.md
python3 scripts/compress.py truncate transcript.md --keep-tokens 4000   # token-budget mode (preferred)
python3 scripts/compress.py truncate transcript.md --keep-head 20 --keep-tail 15
```

Token estimates use `tiktoken` when installed (`pip install tiktoken`), else a fast CJK-aware heuristic (~1 token per CJK char, ~4 chars per token otherwise).

## Example

On a 715-line session transcript (~20.5k tokens) full of retries and noise:

| Stage | Tokens | vs original |
|---|---|---|
| original | 20,513 | — |
| `strip` (noise) | 18,173 | −11% |
| `dedup` | 12,314 | −40% |
| `truncate` (rolling window) | 759 | **−96%** |

Semantic summarization (the `SKILL.md` workflow) compresses further on top of the mechanical pass.

## Layout

```
SKILL.md                 # trigger + 5-step workflow + never-lose checklist
scripts/compress.py      # stdlib-only CLI (count / report / strip / dedup / truncate)
references/strategies.md # compression strategy library
references/agents.md     # per-agent install map + compatibility notes
tests/                   # unit tests (run: python3 -m unittest discover -s tests -v)
```

## Testing

```bash
python3 -m unittest discover -s tests -v
```

GitHub Actions runs these on Python 3.9 / 3.11 / 3.13 on every push and PR.

## License

MIT
