#!/usr/bin/env python3
# patch-v0.9.58b.py — deterministic in-place patch for tests/TestRunner.cs (repo: pedrampedi81-dotcom/smc)
#
# Why this exists (root causes of red CI runs #6/#7, evidence: test-output-v0.9.58.txt):
#   1) COMPILE ERROR in the step-57/58 meta guard: a raw newline was written inside a char
#      literal — srcRunner.Split('<LF>') — so the test project never built (CS1010/CS1011).
#   2) The guard's logic could never go green: it counted EVERY 0.9.N inside Assert/Contains
#      lines, including test DATA ("pico-light 0.9.44") and historical message labels
#      ("v0.9.50: ..."). Only real pins (<Version>0.9.N</Version>, "Classroom Studio v0.9.N",
#      BundleVersion pins) may be counted, and the label form v0.9.N: is excluded.
#   3) The guard read "TestRunner.cs" from the CURRENT directory — on CI the working dir is
#      the repo ROOT, so the file would not be found. Now resolved by walking up from
#      AppContext.BaseDirectory (tests/bin/Release/netX -> ... -> repo root / tests).
#   4) Steps 8/9/14 need C:\Users\wasteland\...\daroon1.amk which only exists on the dev
#      machine — on CI they can never pass. They now print SKIP and stay green when the
#      fixture is absent; on the dev machine they run exactly as before.
#
# Usage (from the repo ROOT, after `git pull`):
#   python tools/patch-v0.9.58b.py
#
# The script is idempotent, keeps a backup at tests/TestRunner.cs.bak-v0.9.58b, verifies
# every anchor before writing, and re-checks brace balance + the pin rule after writing.

import pathlib, shutil, sys

TR = pathlib.Path("tests/TestRunner.cs")
if not TR.exists():
    sys.exit("ERROR: run from the repo root — tests/TestRunner.cs not found")

raw = TR.read_bytes()
CRLF = b"\r\n" in raw
src = raw.decode("utf-8").replace("\r\n", "\n")
lines = src.split("\n")

if "meta guard located TestRunner.cs on disk" in src:
    print("already patched — nothing to do")
    sys.exit(0)

def find_exact(needle_list):
    hits = [i for i in range(0, len(lines) - len(needle_list) + 1)
            if lines[i:i + len(needle_list)] == needle_list]
    if len(hits) != 1:
        sys.exit(f"ERROR: anchor found {len(hits)}x (expected 1): {needle_list[0]!r}")
    return hits[0]

# ---------------------------------------------------------------- meta guard block
meta_start = find_exact(["        // (c) meta guard: every pinned minor in TestRunner matches current version"])
meta_end_hits = [i for i, l in enumerate(lines) if "all pinned version minors match current release" in l]
if len(meta_end_hits) != 1:
    sys.exit("ERROR: meta-guard end anchor not unique")
meta_end = meta_end_hits[0]
if not (meta_start < meta_end):
    sys.exit("ERROR: meta-guard anchors out of order")

META_NEW = r'''        // (c) meta guard: every version PIN in this file matches the current release.
        // Pin lines are the assertions that check the csproj Version tag, the app banner or
        // the Pico bundle version. Version strings inside test DATA (PONG replies like
        // "pico-light 0.9.44") and historical message labels ("v0.9.50: ...") are NOT pins:
        // the label form v0.9.N: is excluded explicitly. v0.9.58b — the first draft had a
        // raw newline inside the char literal (compile error) and counted data strings, so
        // it could never go green; the file path is now resolved by walking up from the
        // build output (CI runs `dotnet run` from the repo root, so the cwd differs).
        string srcRunner = "";
        for (DirectoryInfo? dirWalk = new DirectoryInfo(AppContext.BaseDirectory); dirWalk is not null && srcRunner.Length == 0; dirWalk = dirWalk.Parent)
        {
            foreach (var candPath in new[] { Path.Combine(dirWalk.FullName, "tests", "TestRunner.cs"), Path.Combine(dirWalk.FullName, "TestRunner.cs") })
                if (File.Exists(candPath)) { srcRunner = File.ReadAllText(candPath); break; }
        }
        Assert(srcRunner.Length > 1000, "v0.9.58: meta guard located TestRunner.cs on disk");
        var pinned = new List<int>();
        foreach (var metaLine in srcRunner.Split('\n'))
        {
            if (!metaLine.Contains("<Version>0.9.") && !metaLine.Contains("Classroom Studio v0.9.") && !metaLine.Contains("BundleVersion")) continue;
            foreach (System.Text.RegularExpressions.Match metaMatch in System.Text.RegularExpressions.Regex.Matches(metaLine, @"0\.9\.(\d+)"))
            {
                bool isLabel = metaMatch.Index > 0 && metaLine[metaMatch.Index - 1] == 'v'
                               && metaMatch.Index + metaMatch.Length < metaLine.Length && metaLine[metaMatch.Index + metaMatch.Length] == ':';
                if (!isLabel) pinned.Add(int.Parse(metaMatch.Groups[1].Value));
            }
        }
        var curMinor = 58;
        var pinnedText = string.Join(", ", pinned.Distinct().OrderBy(n => n));
        Assert(pinned.Count > 0 && pinned.Distinct().All(n => n == curMinor),
            $"v0.9.58: all version pins match current release 0.9.{curMinor} (found: {pinnedText})");'''

# ---------------------------------------------------------------- step 8 block (daroon import)
STEP8_OLD = [
    "        var importTask = Task.Run(() =>",
    "            AmkImporter.Import(",
    "                @\"C:\\Users\\wasteland\\Documents\\ams\\pc\\daroon1.amk\",",
    "                @\"C:\\Users\\wasteland\\Documents\\ams\\pc\"));",
    "",
    "        var result = importTask.Wait(TimeSpan.FromSeconds(60)) ? importTask.Result : null;",
    "",
    "        if (result == null)",
    "        {",
    "            Assert(false, \"Import timed out or failed\");",
]
STEP8_NEW = r'''        // v0.9.58b — daroon1.amk lives only on the dev machine; on CI the import/PNG/native steps skip cleanly
        var daroonAmk = @"C:\Users\wasteland\Documents\ams\pc\daroon1.amk";
        var daroonPresent = File.Exists(daroonAmk);
        var importTask = daroonPresent
            ? Task.Run(() => AmkImporter.Import(daroonAmk, @"C:\Users\wasteland\Documents\ams\pc"))
            : null;

        var result = importTask is not null && importTask.Wait(TimeSpan.FromSeconds(60)) ? importTask.Result : null;

        if (result == null)
        {
            if (daroonPresent) Assert(false, "Import timed out or failed");
            else Console.WriteLine("SKIP: daroon1.amk not present on this machine — daroon import test skipped (CI-safe)");'''

# ---------------------------------------------------------------- step 9 tail (PNG extraction)
STEP9_OLD = ["        Assert(pngSuccess, \"PNG images extracted from daroon1.amk\");"]
STEP9_NEW = r'''        if (!pngSuccess && !daroonPresent)
            Console.WriteLine("SKIP: daroon1.amk not present on this machine — PNG extraction test skipped (CI-safe)");
        else
            Assert(pngSuccess, "PNG images extracted from daroon1.amk");'''

# ---------------------------------------------------------------- step 14 block (native extraction)
STEP14_OLD = [
    "            var imgs = AmkImageExtractor.ExtractImages(amkPath, exDir);",
    "            Assert(imgs.Count >= 3, $\"native extractor found embedded pictures (got {imgs.Count}, want >= 3)\");",
    "            Assert(imgs.Count > 0 && imgs.All(File.Exists), \"all extracted PNGs exist on disk\");",
    "            if (imgs.Count > 0)",
    "            {",
    "                using var bmp = new System.Drawing.Bitmap(imgs[0]);",
    "                Assert(bmp.Width > 1 && bmp.Height > 1, $\"extracted image loads with dimensions ({bmp.Width}x{bmp.Height})\");",
    "            }",
]
STEP14_NEW = r'''            if (!daroonPresent)
            {
                Console.WriteLine("SKIP: daroon1.amk not present on this machine — native image extraction test skipped (CI-safe)");
            }
            else
            {
                var imgs = AmkImageExtractor.ExtractImages(amkPath, exDir);
                Assert(imgs.Count >= 3, $"native extractor found embedded pictures (got {imgs.Count}, want >= 3)");
                Assert(imgs.Count > 0 && imgs.All(File.Exists), "all extracted PNGs exist on disk");
                if (imgs.Count > 0)
                {
                    using var bmp = new System.Drawing.Bitmap(imgs[0]);
                    Assert(bmp.Width > 1 && bmp.Height > 1, $"extracted image loads with dimensions ({bmp.Width}x{bmp.Height})");
                }
            }'''

s8 = find_exact(STEP8_OLD)
s9 = find_exact(STEP9_OLD)
s14 = find_exact(STEP14_OLD)

# apply in DESCENDING order so earlier indices stay valid (project lesson)
out = lines[:]
if not (meta_start > s14 > s9 > s8):
    sys.exit(f"ERROR: unexpected anchor order: {s8} {s9} {s14} {meta_start}")
out[meta_start:meta_end + 1] = META_NEW.split("\n")
out[s14:s14 + len(STEP14_OLD)] = STEP14_NEW.split("\n")
out[s9:s9 + 1] = STEP9_NEW.split("\n")
out[s8:s8 + len(STEP8_OLD)] = STEP8_NEW.split("\n")

newsrc = "\n".join(out)

# ---- post-write verification ----
import re
assert "srcRunner.Split('\\n')" in newsrc, "fixed char literal missing"
assert "meta guard located TestRunner.cs on disk" in newsrc
assert newsrc.count("var daroonPresent") == 1 and newsrc.count("daroonPresent") >= 4, "daroon guard wiring wrong"
assert "all pinned version minors match current release" not in newsrc, "old guard text survived"

# delimiter-count identity: new == old - removed + added for every region (catches slice drift)
def raw_counts(s):
    return (s.count('{'), s.count('}'), s.count('('), s.count(')'), s.count('['), s.count(']'))
removed_texts = ["\n".join(lines[s8:s8 + len(STEP8_OLD)]), "\n".join(lines[s9:s9 + 1]),
                 "\n".join(lines[s14:s14 + len(STEP14_OLD)]), "\n".join(lines[meta_start:meta_end + 1])]
added_texts = [STEP8_NEW, STEP9_NEW, STEP14_NEW, META_NEW]
for i, sym in enumerate(['{', '}', '(', ')', '[', ']']):
    exp = raw_counts(src)[i] - sum(t.count(sym) for t in removed_texts) + sum(t.count(sym) for t in added_texts)
    if raw_counts(newsrc)[i] != exp:
        sys.exit(f"ERROR: delimiter {sym!r} count drift: expected {exp}, got {raw_counts(newsrc)[i]} — NOT writing")

# no raw newline may remain inside a char literal
for i, l in enumerate(out):
    if l.rstrip().endswith("'") and i + 1 < len(out) and out[i + 1].startswith("')"):
        sys.exit(f"ERROR: broken char literal still present near line {i + 1}")

# pin simulation of the NEW guard against the NEW file
pins = []
for l in out:
    if '<Version>0.9.' in l or 'Classroom Studio v0.9.' in l or 'BundleVersion' in l:
        for m in re.finditer(r'0\.9\.(\d+)', l):
            is_label = m.start() > 0 and l[m.start() - 1] == 'v' and m.end() < len(l) and l[m.end()] == ':'
            if not is_label:
                pins.append(int(m.group(1)))
if not pins or any(n != 58 for n in pins):
    sys.exit(f"ERROR: pin guard would fail — {sorted(set(pins))}")

shutil.copyfile(TR, TR.with_suffix(".cs.bak-v0.9.58b"))
TR.write_bytes(newsrc.replace("\n", "\r\n").encode("utf-8") if CRLF else newsrc.encode("utf-8"))
print(f"OK: patched {TR} ({len(lines)} -> {len(out)} lines, backup: {TR.with_suffix('.cs.bak-v0.9.58b')})")
print("next: dotnet run --project tests/TestRunner -c Release   (expect 0 failed)")
print("then: git add tests/TestRunner.cs && git commit && git push")
