# Installation & Compatibility Map

The skill is plain Markdown + Python 3 stdlib, so it works with virtually every agent. "Install" means: make the agent load SKILL.md when context compression is needed.

## Per-agent placement

| Agent | Where to put it | How it activates |
|---|---|---|
| OpenSquilla | `skills/context-compressor/` (workspace), `.agents/skills/` (project), `~/.agents/skills/` (personal) | Skill registry auto-triggers on description match |
| Claude Code | `~/.claude/skills/context-compressor/` (personal) or `.claude/skills/context-compressor/` (project) | Skills feature loads SKILL.md on trigger |
| Codex (OpenAI) | `.agents/skills/` or the skills directory referenced from AGENTS.md | Reads SKILL.md as agent instructions |
| Cursor | `.cursor/rules/context-compressor.mdc` (project) or global rules | Rules load as context; or reference the folder path from a rule |
| Windsurf | `.windsurf/rules/context-compressor.md` | Rules load as context |
| OpenCode / Aider / Continue / Cline | Point the agent at `SKILL.md` (e.g. `@context-compressor/SKILL.md` or a rule file) | Manual or rule-based |

Check the agent's current docs — directory paths and feature names move.

## Rule-file agents (Cursor, Windsurf, ...)

They load rules as static context and cannot "call" a skill. Two options:

1. Embed the "When to compress + workflow + never-lose checklist" sections (compact by design) into the rules file.
2. Reference the folder and keep the full SKILL.md + script next to the project.

## Script compatibility

- `scripts/compress.py` uses Python 3 stdlib only; works on Windows/macOS/Linux.
- Token estimates use `tiktoken` when importable (`pip install tiktoken`), otherwise a CJK-aware heuristic — values differ slightly between the two but stay consistent.
- No network access, no config files, no secrets.

## Quick port recipe

1. Copy the `context-compressor/` folder into the agent's skill or rules directory (see table).
2. Ensure the trigger words ("压缩上下文", "save tokens", "compact context", ...) appear in the description or rule text.
3. Keep `scripts/compress.py` next to SKILL.md so `python3 scripts/compress.py ...` works as documented.
