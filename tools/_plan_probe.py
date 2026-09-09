#!/usr/bin/env python3
"""TEMPORARY read-only probe.

Locates every place the Pico firmware sources touch the plan engine so the
diagnostic build can be written against exact anchors. Writes plain text to
stdout; the temp workflow captures it into reports/plan-diag.txt.

This file and its workflow are deleted before any PR is opened.
"""
import hashlib
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "node_modules", "bin", "obj", "artifacts", ".vs"}
TEXT_EXT = {".py", ".txt", ".md", ".cs", ".yml", ".yaml"}
MAX_LINE = 200
VER_RE = re.compile(r"0\.9\.\d+[a-z]?")


def walk():
    out = []
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            path = os.path.join(base, name)
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            out.append((path, rel))
    out.sort(key=lambda t: t[1])
    return out


def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


FILES = walk()

print("=== 1. PYTHON INVENTORY (firmware/, portable/, tools/, ams-shell/bridge/) ===")
for path, rel in FILES:
    if not rel.endswith(".py"):
        continue
    if not rel.startswith(("firmware/", "portable/", "tools/", "ams-shell/bridge/")):
        continue
    body = read(path)
    vers = sorted(set(VER_RE.findall(body)))
    print("%-50s %8d  %s  vers=%s" % (rel, os.path.getsize(path), sha256(path)[:16], ",".join(vers[:10]) or "-"))
print()

print("=== 2. HEAD OF EACH FIRMWARE FILE (first 24 lines) ===")
for path, rel in FILES:
    if not rel.endswith(".py"):
        continue
    if not rel.startswith(("firmware/", "portable/")):
        continue
    print("--- %s ---" % rel)
    for i, line in enumerate(read(path).splitlines()[:24], 1):
        print("%5d| %s" % (i, line[:MAX_LINE]))
    print()

PATTERNS = [
    ("plan_engine", re.compile(r"plan_engine")),
    ("run_plan", re.compile(r"run_plan")),
    ("plan_pass", re.compile(r"plan_pass")),
    ("_pe token", re.compile(r"(?<![A-Za-z0-9_])_pe(?![A-Za-z0-9_])")),
    ("0.9.66", re.compile(r"0\.9\.66")),
    ("plan.txt", re.compile(r"plan\.txt")),
    ("except Exception", re.compile(r"except Exception")),
]

print("=== 3. GREP ===")
for label, rx in PATTERNS:
    print("--- pattern: %s ---" % label)
    hits = 0
    for path, rel in FILES:
        if os.path.splitext(rel)[1] not in TEXT_EXT:
            continue
        for i, line in enumerate(read(path).splitlines(), 1):
            if rx.search(line):
                hits += 1
                if hits <= 60:
                    print("%s:%d: %s" % (rel, i, line.strip()[:MAX_LINE]))
    print("(total hits: %d)" % hits)
    print()

CTX_RE = re.compile(r"(plan_engine|(?<![A-Za-z0-9_])_pe(?![A-Za-z0-9_])|run_plan|plan_pass|plan\.txt|PLAN\|)")

print("=== 4. CONTEXT DUMPS (firmware/ and portable/ python files) ===")
for path, rel in FILES:
    if not rel.endswith(".py"):
        continue
    if not rel.startswith(("firmware/", "portable/")):
        continue
    body = read(path)
    if "plan_engine" not in body and "run_plan" not in body:
        continue
    lines = body.splitlines()
    marks = [i for i, line in enumerate(lines) if CTX_RE.search(line)]
    if not marks:
        continue
    ranges = []
    for m in marks:
        lo = max(0, m - 8)
        hi = min(len(lines), m + 9)
        if ranges and lo <= ranges[-1][1]:
            ranges[-1][1] = max(ranges[-1][1], hi)
        else:
            ranges.append([lo, hi])
    print("--- %s (%d lines, %d marks, %d ranges) ---" % (rel, len(lines), len(marks), len(ranges)))
    printed = 0
    for lo, hi in ranges:
        if printed > 520:
            print("  ... (context truncated)")
            break
        print("  @@ %d-%d" % (lo + 1, hi))
        for i in range(lo, hi):
            print("  %5d| %s" % (i + 1, lines[i][:MAX_LINE]))
            printed += 1
        print()
    print()

print("=== 5. plan_engine.py PUBLIC API ===")
PE = os.path.join(ROOT, "firmware", "code64b", "plan_engine.py")
if os.path.exists(PE):
    for i, line in enumerate(read(PE).splitlines(), 1):
        if re.match(r"^(def |class |[A-Z_]{2,} *=|    def )", line):
            print("%5d| %s" % (i, line[:MAX_LINE]))
else:
    print("firmware/code64b/plan_engine.py: MISSING")
print()

print("=== 6. code64b_check.py ASSERT LABELS ===")
CHK = os.path.join(ROOT, "firmware", "code64b", "code64b_check.py")
if os.path.exists(CHK):
    for i, line in enumerate(read(CHK).splitlines(), 1):
        if "check(" in line or "def " in line:
            print("%5d| %s" % (i, line.strip()[:MAX_LINE]))
else:
    print("firmware/code64b/code64b_check.py: MISSING")
print()

print("=== END OF PROBE ===")
