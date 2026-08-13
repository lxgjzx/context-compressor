#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Context Compressor — token counting and mechanical compression helpers.

Pure Python 3 stdlib (no dependencies) so it runs on virtually any agent
host: Claude Code, Codex, Cursor, Windsurf, OpenSquilla, etc.
If `tiktoken` is importable it is used for more accurate token estimates;
otherwise a fast CJK-aware heuristic (~1 token per CJK char, ~4 chars per
token otherwise) is used.

Subcommands:
  count     Estimate tokens for files (or stdin with --stdin).
  truncate  Keep first N and last M lines; replace the middle with a marker.
  dedup     Remove duplicate lines; collapse runs of blank lines.
  strip     Remove ANSI escapes, noise lines, and long base64 blobs.
  report    Print a before/after token table for a batch of files.

All destructive subcommands default to in-place writes; pass --dry-run to
print the result without writing.
"""

import argparse
import json
import re
import sys

try:
    # Respect the host locale (UTF-8 on Linux/macOS, ANSI/GBK on Windows
    # consoles) so CJK paths/names render correctly. errors="replace" only
    # prevents crashes on unmappable characters.
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]")
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
BASE64_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")

NOISE_RE = [
    re.compile(r"^\s*[\-=_*#~]{8,}\s*$"),  # separator lines
    re.compile(r"^\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})?\s*\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\s*$"),  # lone timestamps
    re.compile(r"^\s*(ok|ok\.|done|received|sent|exit code 0)\s*$", re.IGNORECASE),
]


def _tiktoken_count(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return -1


def estimate_tokens(text: str) -> float:
    n = _tiktoken_count(text)
    if n >= 0:
        return float(n)
    cjk = len(CJK_RE.findall(text))
    rest = len(CJK_RE.sub("", text))
    return cjk + rest / 4.0


def read_lines(path: str):
    # utf-8-sig transparently strips a leading BOM (e.g. PowerShell-written
    # files) so it doesn't contaminate first-line matching or token counts.
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.readlines()


def write_lines(path: str, lines) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(lines)


def is_base64_line(line: str) -> bool:
    s = line.strip()
    if len(s) < 120:
        return False
    letters = [c for c in s if not c.isspace()]
    if not letters:
        return False
    hits = sum(1 for c in letters if c in BASE64_CHARS)
    return hits / len(letters) >= 0.85


def cmd_count(args) -> None:
    if args.stdin:
        text = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        if args.json:
            print(json.dumps([{"path": "stdin", "tokens_est": round(estimate_tokens(text))}]))
        else:
            print(f"stdin\t{estimate_tokens(text):.0f}")
        return
    results = []
    for path in args.files:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
        results.append((path, estimate_tokens(text)))
    if args.json:
        print(json.dumps([{"path": p, "tokens_est": round(t)} for p, t in results]))
    else:
        for p, t in results:
            print(f"{p}\t{t:.0f}")


def cmd_truncate(args) -> None:
    lines = read_lines(args.file)
    head, tail = max(0, args.keep_head), max(0, args.keep_tail)
    before_tokens = estimate_tokens("".join(lines))
    if head + tail >= len(lines):
        out = lines
    else:
        removed = lines[head : len(lines) - tail]
        dropped = len(removed)
        dropped_tokens = estimate_tokens("".join(removed))
        marker = f"... [compressed: dropped {dropped} lines, ~{dropped_tokens:.0f} tokens] ...\n"
        out = lines[:head] + [marker] + lines[len(lines) - tail :]
    after_tokens = estimate_tokens("".join(out))
    if args.dry_run:
        sys.stdout.write("".join(out))
    else:
        write_lines(args.out or args.file, out)
    saved_pct = 100 * (1 - after_tokens / before_tokens) if before_tokens > 0 else 0.0
    print(
        f"# {args.file}: {len(lines)} -> {len(out)} lines, "
        f"~{before_tokens:.0f} -> ~{after_tokens:.0f} tokens "
        f"({saved_pct:.0f}% saved)",
        file=sys.stderr,
    )


def cmd_dedup(args) -> None:
    lines = read_lines(args.file)
    seen = set()
    out = []
    prev_blank = False
    for line in lines:
        key = line.strip()
        if args.ignore_case:
            key = key.lower()
        if not key:
            if not prev_blank:
                out.append("\n")
            prev_blank = True
            continue
        prev_blank = False
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    before_tokens = estimate_tokens("".join(lines))
    after_tokens = estimate_tokens("".join(out))
    if args.dry_run:
        sys.stdout.write("".join(out))
    else:
        write_lines(args.out or args.file, out)
    print(
        f"# {args.file}: {len(lines)} -> {len(out)} lines, "
        f"~{before_tokens:.0f} -> ~{after_tokens:.0f} tokens",
        file=sys.stderr,
    )


def cmd_strip(args) -> None:
    lines = read_lines(args.file)
    user_re = None
    if args.pattern:
        try:
            user_re = re.compile(args.pattern)
        except re.error as e:
            print(f"error: invalid --pattern regex: {e}", file=sys.stderr)
            sys.exit(2)
    out = []
    prev_blank = False
    for line in lines:
        line = ANSI_RE.sub("", line)
        stripped = line.strip()
        if user_re and user_re.search(line):
            continue
        if is_base64_line(line):
            continue
        if any(r.match(line) for r in NOISE_RE):
            continue
        if not stripped:
            if not prev_blank:
                out.append("\n")
            prev_blank = True
            continue
        prev_blank = False
        out.append(line)
    before_tokens = estimate_tokens("".join(lines))
    after_tokens = estimate_tokens("".join(out))
    if args.dry_run:
        sys.stdout.write("".join(out))
    else:
        write_lines(args.out or args.file, out)
    print(
        f"# {args.file}: {len(lines)} -> {len(out)} lines, "
        f"~{before_tokens:.0f} -> ~{after_tokens:.0f} tokens",
        file=sys.stderr,
    )


def cmd_report(args) -> None:
    rows = []
    for path in args.files:
        lines = read_lines(path)
        orig = estimate_tokens("".join(lines))
        prev_blank = False
        seen = set()
        cur = []
        for line in lines:
            line = ANSI_RE.sub("", line)
            key = line.strip().lower() if args.ignore_case else line.strip()
            if not key:
                if not prev_blank:
                    cur.append("\n")
                prev_blank = True
                continue
            prev_blank = False
            if key in seen:
                continue
            seen.add(key)
            if is_base64_line(line) or any(r.match(line) for r in NOISE_RE):
                continue
            cur.append(line)
        cleaned = estimate_tokens("".join(cur))
        rows.append((path, orig, cleaned))
    if args.json:
        print(json.dumps([{"path": p, "before": round(b), "after_clean": round(c)} for p, b, c in rows]))
        return
    width = max(len(p) for p, _, _ in rows) if rows else 8
    print(f"{'file'.ljust(width)}  {'before':>10}  {'after':>10}  {'saved':>7}")
    for p, b, c in rows:
        pct = 100 * (1 - c / b) if b else 0
        print(f"{p.ljust(width)}  {b:>10.0f}  {c:>10.0f}  {pct:>6.0f}%")


def main() -> None:
    parser = argparse.ArgumentParser(prog="compress.py", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_count = sub.add_parser("count", help="estimate tokens for files or stdin")
    p_count.add_argument("files", nargs="*")
    p_count.add_argument("--stdin", action="store_true", help="read text from stdin")
    p_count.add_argument("--json", action="store_true")
    p_count.set_defaults(func=cmd_count)

    p_trunc = sub.add_parser("truncate", help="keep head/tail lines, mark the middle")
    p_trunc.add_argument("file")
    p_trunc.add_argument("--keep-head", type=int, default=20)
    p_trunc.add_argument("--keep-tail", type=int, default=15)
    p_trunc.add_argument("-o", "--out")
    p_trunc.add_argument("--dry-run", action="store_true")
    p_trunc.set_defaults(func=cmd_truncate)

    p_dedup = sub.add_parser("dedup", help="remove duplicate lines, collapse blanks")
    p_dedup.add_argument("file")
    p_dedup.add_argument("-o", "--out")
    p_dedup.add_argument("--ignore-case", action="store_true")
    p_dedup.add_argument("--dry-run", action="store_true")
    p_dedup.set_defaults(func=cmd_dedup)

    p_strip = sub.add_parser("strip", help="remove ANSI, noise lines, base64 blobs")
    p_strip.add_argument("file")
    p_strip.add_argument("--pattern", help="extra regex of lines to drop")
    p_strip.add_argument("-o", "--out")
    p_strip.add_argument("--dry-run", action="store_true")
    p_strip.set_defaults(func=cmd_strip)

    p_report = sub.add_parser("report", help="before/after token table for files")
    p_report.add_argument("files", nargs="+")
    p_report.add_argument("--ignore-case", action="store_true")
    p_report.add_argument("--json", action="store_true")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
