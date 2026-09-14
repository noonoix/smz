from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def edit(rel, fn):
    p = ROOT / rel
    old = p.read_text(encoding="utf-8")
    new = fn(old)
    if new != old:
        p.write_text(new, encoding="utf-8")
        print("updated", rel)


def patch_xaml(text):
    if 'Header="Key _Hold Group"' not in text:
        pair = re.compile(r'(?ms)^(?P<indent>[ \t]*)<MenuItem Header="Key _Down".*?/>[ \t]*\n(?P=indent)<MenuItem Header="Key _Up".*?/>')
        text, count = pair.subn(lambda m: m.group(0).splitlines()[0].replace('Header="Key _Down"', 'Header="Key _Hold Group"').replace('CommandParameter="keyDown"', 'CommandParameter="keyHold"'), text)
        if count == 0:
            raise RuntimeError("top Insert Key Down/Key Up pair not found")

    if 'Header="Run/Call _Main DC Recovery"' not in text:
        pattern = re.compile(r'(?ms)^(?P<indent>[ \t]*)<MenuItem Header="Run/Call _Launch DC Recovery".*?/>')
        match = pattern.search(text)
        if not match:
            raise RuntimeError("top Launch recovery menu item not found")
        launch = match.group(0)
        main = launch.replace('callLaunchDcRecovery', 'callMainDcRecovery')
        main = main.replace('_Launch', '_Main').replace('launch_recovery', 'main_recovery').replace('IsLaunchPipeline', 'IsMainPipeline')
        text = text[:match.end()] + "\n" + match.group('indent') + main.lstrip() + text[match.end():]
    return text


def patch_vm(text):
    text = text.replace(
        '        foreach (var root in Steps.ToList())\n            changed |= NormalizeKeyList(root.Parent?.Children ?? Steps);',
        '        changed = NormalizeKeyList(Steps);',
        1,
    )
    if 'bool opensKeyHold = n.Type == "keyHold";' not in text:
        text = text.replace(
            '                bool opensParallel = n.Type == "parallelGroup";   // v0.9.44 — a Parallel Group with children registers its scope too, so its red vein shows (user report)\n',
            '                bool opensParallel = n.Type == "parallelGroup";   // v0.9.44 — a Parallel Group with children registers its scope too, so its red vein shows (user report)\n\n                bool opensKeyHold = n.Type == "keyHold";\n',
            1,
        )
    text = text.replace(
        '                if (opensLoop || opensIf || opensPackage || opensParallel)   // v0.9.44 — parallelGroup added: its children must show the red vein\n',
        '                if (opensLoop || opensIf || opensPackage || opensParallel || opensKeyHold)   // atomic Key Hold groups use the same red scope rail\n',
        1,
    )
    return text


edit("ams-shell/src/Ams.UI/MainWindow.xaml", patch_xaml)
edit("ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs", patch_vm)
