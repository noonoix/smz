#!/usr/bin/env python3
# patch-v0.9.58c.py — CI-convergence patch (repo: pedrampedi81-dotcom/smc)
#
# Why this exists:
#   Run #9 — the first run with real logs — was "668 passed, 1 failed" while the dev machine
#   is 689/0. The single CI-only failure is a wall-clock CEILING in the parallel-group tests:
#   shared GitHub runners stretch Task.Delay under load, so a ceiling that asserts "fast
#   enough" (520ms/750ms) can trip there while passing on the dev box. That is a machine
#   property, not correctness. The overlap/join PROPERTY stays pinned everywhere by the
#   deterministic MaxInFlight asserts and by the floor asserts (which remain HARD).
#
#   This patch makes ONLY the ceilings diagnostic-only when GITHUB_ACTIONS=true (hard asserts
#   everywhere else), and patches .github/workflows/build.yml so a red run's issue body
#   includes every FAIL:/SKIP:/error line — the next failure names itself.
#
# Usage (from the repo ROOT, after `git pull` — you need CI v5.2 from main first):
#   python tools/patch-v0.9.58c.py
#   dotnet run --project tests/TestRunner -c Release    (expect 0 failed)
#   git add tests/TestRunner.cs .github/workflows/build.yml
#   git commit -m "fix(tests): v0.9.58c — CI-safe timing ceilings + FAIL lines in CI issues"
#   git push
#
# Idempotent; refuses to write if any anchor is missing (git is the backup).

import pathlib, re, sys

TR = pathlib.Path("tests/TestRunner.cs")
WF = pathlib.Path(".github/workflows/build.yml")
if not TR.exists() or not WF.exists():
    sys.exit("ERROR: run from the repo root (tests/TestRunner.cs / .github/workflows/build.yml not found)")

def load(p):
    raw = p.read_bytes()
    crlf = b"\r\n" in raw
    return raw.decode("utf-8").replace("\r\n", "\n"), crlf

def save(p, text, crlf):
    p.write_bytes(text.replace("\n", "\r\n").encode("utf-8") if crlf else text.encode("utf-8"))

def splice(name, src, old, new):
    n = src.count(old)
    if n != 1:
        sys.exit(f"ERROR: anchor for edit {name} found {n}x (expected 1) — file changed? did you `git pull`?")
    return src.replace(old, new)

src, tr_crlf = load(TR)
wf, wf_crlf = load(WF)

# preflight: the workflow must already be CI v5.2 (it carries a "Build TestRunner" step)
if "failLines" not in wf and "Build TestRunner" not in wf:
    sys.exit("ERROR: workflow is not CI v5.2 — run `git pull` first (main already has the v5.2 fix)")

changed_tr = changed_wf = False

# ---------------------------------------------------------------- tests/TestRunner.cs
if "bool IsCi" in src:
    print("tests/TestRunner.cs: already patched — skipping")
else:
    src = splice("C (IsCi helper)", src,
        "    static int passed = 0, failed = 0;",
        "    static int passed = 0, failed = 0;\n"
        "    // v0.9.58c — wall-clock ceilings are machine properties and flake on shared CI runners\n"
        "    static readonly bool IsCi = Environment.GetEnvironmentVariable(\"GITHUB_ACTIONS\") == \"true\";")

    src = splice("A (overlap ceiling)", src,
        "        sw.Stop();\n"
        "        Assert(sw.ElapsedMilliseconds < 520,\n"
        "            $\"parallel group: two 300ms delays overlap (elapsed {sw.ElapsedMilliseconds}ms; sequential would be ≥600)\");",
        "        sw.Stop();\n"
        "        // v0.9.58c — ceiling is diagnostic-only on CI; overlap itself is proven by MaxInFlight asserts\n"
        "        if (IsCi) Console.WriteLine($\"INFO(CI): two 300ms branches overlapped, elapsed {sw.ElapsedMilliseconds}ms\");\n"
        "        else Assert(sw.ElapsedMilliseconds < 520,\n"
        "            $\"parallel group: two 300ms delays overlap (elapsed {sw.ElapsedMilliseconds}ms; sequential would be ≥600)\");")

    src = splice("B (join ceiling)", src,
        "        Assert(sw.ElapsedMilliseconds >= 400 && sw.ElapsedMilliseconds < 750,\n"
        "            $\"parallel group joins on the LONGEST branch (elapsed {sw.ElapsedMilliseconds}ms ≈ 450, not 570)\");",
        "        Assert(sw.ElapsedMilliseconds >= 400,\n"
        "            $\"parallel group join blocks until the longest branch finishes (elapsed {sw.ElapsedMilliseconds}ms, floor 400)\");\n"
        "        // v0.9.58c — ceiling is diagnostic-only on CI (loaded runners stretch delays)\n"
        "        if (IsCi) Console.WriteLine($\"INFO(CI): longest-branch join elapsed {sw.ElapsedMilliseconds}ms (≈450 nominal)\");\n"
        "        else Assert(sw.ElapsedMilliseconds < 750,\n"
        "            $\"parallel group joins on the LONGEST branch (elapsed {sw.ElapsedMilliseconds}ms ≈ 450, not 570)\");")

    # the floor asserts (>= 400 here, >= 380 in the after-join test) stay HARD everywhere —
    # they pin the join semantics (blocking), not the speed.

    # verify: IsCi wired exactly once + used twice; meta-guard pin simulation still all-58
    if src.count("static readonly bool IsCi") != 1 or src.count("IsCi") != 3:
        sys.exit("ERROR: IsCi wiring wrong (expected 1 declaration + 2 uses)")
    pins = []
    for l in src.split("\n"):
        if '<Version>0.9.' in l or 'Classroom Studio v0.9.' in l or 'BundleVersion' in l:
            for m in re.finditer(r'0\.9\.(\d+)', l):
                is_label = m.start() > 0 and l[m.start() - 1] == 'v' and m.end() < len(l) and l[m.end()] == ':'
                if not is_label:
                    pins.append(int(m.group(1)))
    if not pins or any(n != 58 for n in pins):
        sys.exit(f"ERROR: meta guard would fail after patch — {sorted(set(pins))}")
    save(TR, src, tr_crlf)
    changed_tr = True
    print("OK: tests/TestRunner.cs — timing ceilings are CI-diagnostic (floors + MaxInFlight stay hard)")

# ---------------------------------------------------------------- .github/workflows/build.yml
if "failLines" in wf:
    print("workflow: already patched — skipping")
else:
    wf = splice("W1 (collect failure lines)", wf,
        r"""            const tail = read('ci-test-output.txt').split('\n').slice(-60).join('\n');""",
        r"""            const allLines = read('ci-test-output.txt').split('\n');""" + "\n" +
        r"""            const failLines = allLines.filter(l => /^(FAIL:|SKIP:)|error CS|error MSB|Build FAILED/i.test(l)).slice(-40);""" + "\n" +
        r"""            const tail = allLines.slice(-60).join('\n');""")

    wf = splice("W2 (issue body shows them)", wf,
        r"""                + '\n\n**Test log tail:**\n```\n' + (tail || '(no test log — failure before the test step)') + '\n```'""",
        r"""                + '\n\n**Failure lines:**\n```\n' + (failLines.join('\n') || '(none matched)') + '\n```'""" + "\n" +
        r"""                + '\n\n**Test log tail:**\n```\n' + (tail || '(no test log — failure before the test step)') + '\n```'""")

    save(WF, wf, wf_crlf)
    changed_wf = True
    print("OK: .github/workflows/build.yml — red issues now list their FAIL/SKIP/error lines")

print()
if changed_tr or changed_wf:
    print("next: dotnet run --project tests/TestRunner -c Release   (expect 0 failed)")
    print("then: git add tests/TestRunner.cs .github/workflows/build.yml")
    print('      git commit -m "fix(tests): v0.9.58c — CI-safe timing ceilings + FAIL lines in CI issues"')
    print("      git push")
else:
    print("nothing to do")
