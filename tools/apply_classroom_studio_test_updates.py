from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "tests" / "TestRunner.cs"
text = path.read_text(encoding="utf-8")
original = text

# The rail now exposes one atomic keyboard action. Key Down/Key Up remain legacy
# model types for import compatibility, but are no longer independent Insert entries.
text = text.replace(
    '"keystroke", "typeText", "keyDown", "keyUp", "delay"',
    '"keystroke", "typeText", "keyHold", "delay"',
    1,
)

old = '''        // 4-10) every keyboard step has Default/Pico/Pro Micro override with safe transport behavior
        foreach (var type in new[] { "keystroke", "typeText", "keyDown", "keyUp" })
        {
            var field = StepDefinitions.Get(type).Fields.SingleOrDefault(f => f.Key == "keyboardBoard");
            Assert(field is not null && field.Options is not null
                   && field.Options.SequenceEqual(new[] { "default", "pico", "promicro" }),
                $"v0.9.46: {type} exposes default/pico/promicro keyboard executor");
        }
'''
new = '''        // 4-10) keyboard executor is global Options state; the old per-step dropdown
        // was intentionally removed so action rows cannot disagree with the active board.
        foreach (var type in new[] { "keystroke", "typeText", "keyDown", "keyUp" })
        {
            var field = StepDefinitions.Get(type).Fields.SingleOrDefault(f => f.Key == "keyboardBoard");
            Assert(field is null,
                $"v0.9.67: {type} no longer exposes a duplicate per-step keyboard executor");
        }
        var keyHoldDef = StepDefinitions.Get("keyHold");
        Assert(keyHoldDef.IsContainer && keyHoldDef.IsScopeContainer
               && keyHoldDef.Fields.Any(f => f.Key == "key"),
            "v0.9.67: Key Hold is one atomic scope action with a held-key field");
'''
if old in text:
    text = text.replace(old, new, 1)
elif 'v0.9.67: {type} no longer exposes a duplicate per-step keyboard executor' not in text:
    raise RuntimeError("keyboard executor assertion block not found")

if text != original:
    path.write_text(text, encoding="utf-8")
    print("updated tests/TestRunner.cs")
else:
    print("tests/TestRunner.cs already matches the new action contracts")
