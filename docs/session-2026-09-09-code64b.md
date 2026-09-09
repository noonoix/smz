# Session 2026-09-09 — code64b: GP4 start/stop cursor teleport fixed

Mirror of this session's produced artifacts (rule 10). The user's original code64 zip and the
raw 426 KB record stay in this session's chat attachments (not mirrored here).

## Symptom (user report)
On code64 (pico-light 0.9.64, the working golden base): after moving the physical mouse to the
LEFT of the screen, every GP4 Stop/Start snapped the cursor back by itself to specific spots on
the RIGHT side — the plan's stored positions.

## Evidence (analysis/record_summary_compact.json, produced by analysis/analyze_record.py)
Record: 75.9 s, 4,985 position samples, 43 key events, 14 GP4 (Num Lock) toggles.
- 5 snaps of 964–1216 px in the SAME millisecond as the keypress:
  toggle 1: (347,331)->(1388,725); toggle 6: (495,388)->(1408,697) in 42 ms;
  toggle 9: (412,535)->(1453,862) — byte-identical to the pre-stop position (smoking gun);
  toggle 11: (346,363)->(1536,612); toggle 13: (362,337)->(1543,265).
- Each snap is trailed by exactly 3 identical position reports = the 3 MUP reports.
- Toggles with the mouse untouched: 0 px jump (9/14) — code64's persistence works.
- 0 phantom clicks; median movement step 2.83 px (healthy humanization).

## Root cause
release_all_buttons() (the v0.9.63 shield) sent unconditional MUP x3 on every GP4 start AND stop.
Arm fw >= 1.8 runs cursor_sync() before EVERY button report and embeds its tracked axes (= last
plan MMOVE, right side) into the report -> each pointless MUP teleported the cursor in the
keypress millisecond. When the mouse had not moved, tracked == actual and the snap was invisible.

## Fix — firmware/code64b/ (pico-light 0.9.64b), Pico-side only
- _held_buttons tracked in forward_fast (MDOWN add / MUP discard).
- release_all_buttons(force=False): routine start/stop releases only genuinely held buttons —
  empty set = zero MUP = zero cursor_sync = zero teleport.
- force=True keeps the full three-button shield on abnormal paths (host HALT/BYE, plan abort,
  run error).
- Panic gesture: GP4 held >= 1 s -> force release x3 + led_fault(5).
- plan_engine.py and plan.txt byte-identical to code64; arm fw 2.2 untouched.
- tools/make_code64b.py rebuilds code64b.py from code64.py via 16 anchored, count-asserted edits.
- code64b_check.py: 34/34 pass (17 static + 17 behavioural). Retraction: old T1c/T2 had locked
  the unconditional MUP x3 — that behaviour was the bug and is inverted by design.

## Hashes (sha256)
- code64b.py: 124eae5296d826162abc5261ed5f2ef869e71754fc805c9777002ad19ba6cc6e (35,974 bytes)
- Classroom-Studio-code64b.zip: 74fc438970f067365102356fa66e4097a177a55020fe98fd1e0e0d5d56f7daab
- originals (user zip): code64.py 7560b0021716..., plan_engine.py 187e8d1c1c..., plan.txt bd549f13...

## Mirror fidelity
Every mirrored file was verified byte-identical to the sandbox original via git blob sha + size,
with ONE exception: the repo copy of plan_engine.py differs from the golden file only by a
header-comment word ("TypeScript" instead of "TypeTextCommands") plus <=2 whitespace bytes
(repo blob 32,294 B vs golden 32,298 B). It is functionally identical — code64b_check.py (34/34)
executes it (T9/T10/S14/S15). Byte-perfect golden copies: the user's original code64 zip and the
delivered Classroom-Studio-code64b.zip in this session's chat attachments.

## Known limit (unchanged)
HID has no position feedback: after a manual move + Start, the plan's first move (~0.5 s later)
still re-homes the cursor into the plan region — that is the plan doing its job, not a keypress
snap. Complete fix = app-side Cursor.Position sync (queued for the C# line).

## Status
Zip delivered in chat; acceptance test = move the mouse left while stopped -> Stop/Start -> the
cursor must not snap; the boot banner must read pico-light 0.9.64b. The 0.9.66 portable
regression line is on hold (user returned to the code64 golden base).
