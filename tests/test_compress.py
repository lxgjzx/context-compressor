"""Unit tests for scripts/compress.py.

Runs the CLI as a subprocess so it also guards against import-time regressions.
No third-party dependencies; uses only stdlib unittest + subprocess.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "compress.py"


def run(*args, stdin=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class TestCount(unittest.TestCase):
    def test_count_basic(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.md"
            p.write_text("hello world\n" * 10, encoding="utf-8")
            r = run("count", str(p), "--json")
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(len(data), 1)
            self.assertGreater(data[0]["tokens_est"], 0)

    def test_count_stdin(self):
        r = run("count", "--stdin", "--json", stdin="你好世界 hello world")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data[0]["path"], "stdin")
        self.assertGreater(data[0]["tokens_est"], 0)


class TestDedup(unittest.TestCase):
    def test_dedup_removes_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.md"
            p.write_text("a\nb\nb\nc\n", encoding="utf-8")
            out = Path(d) / "o.md"
            r = run("dedup", str(p), "--out", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(out.read_text(encoding="utf-8").splitlines(), ["a", "b", "c"])


class TestStrip(unittest.TestCase):
    def test_strip_removes_ansi_and_noise(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.md"
            p.write_text("\x1b[32mok\x1b[0m\nhello\n", encoding="utf-8")
            out = Path(d) / "o.md"
            r = run("strip", str(p), "--out", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            content = out.read_text(encoding="utf-8")
            self.assertIn("hello", content)      # real content kept
            self.assertNotIn("ok", content)      # noise line dropped

    def test_strip_bom_removed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.md"
            p.write_text("# title\nbody\n", encoding="utf-8-sig")  # BOM file
            out = Path(d) / "o.md"
            r = run("strip", str(p), "--out", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            content = out.read_text(encoding="utf-8")
            self.assertFalse(content.startswith("\ufeff"))


class TestTruncate(unittest.TestCase):
    def test_truncate_keeps_head_and_tail(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.md"
            p.write_text("".join(f"line{i}\n" for i in range(20)), encoding="utf-8")
            out = Path(d) / "o.md"
            r = run("truncate", str(p), "--keep-head", "2", "--keep-tail", "3", "--out", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            content = out.read_text(encoding="utf-8")
            self.assertIn("line0", content)
            self.assertIn("line19", content)
            self.assertIn("compressed", content)

    def test_truncate_empty_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "empty.md"
            p.write_text("", encoding="utf-8")
            r = run("truncate", str(p), "--dry-run")
            self.assertEqual(r.returncode, 0, r.stderr)


class TestReport(unittest.TestCase):
    def test_report_prints_before_after(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.md"
            p.write_text("a\nb\nb\nc\n", encoding="utf-8")
            r = run("report", str(p))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("before", r.stdout)
            self.assertIn("after", r.stdout)


if __name__ == "__main__":
    unittest.main()
