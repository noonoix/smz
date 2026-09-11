#!/usr/bin/env python3
"""Cut the Classroom Studio 0.9.66 app release while preserving accepted firmware pins.

Idempotent release-branch patch: app 0.9.65 -> 0.9.66; Pico bundle remains
0.9.64f and the accepted Pro Micro baseline remains 2.5.
"""
from pathlib import Path
import re
import sys

APP_OLD = "0.9.65"
APP = "0.9.66"
BUNDLE = "0.9.64f"
CSPROJ = Path("ams-shell/src/Ams.UI/Ams.UI.csproj")
VM = Path("ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs")
EXPORTER = Path("ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs")
RUNNER = Path("tests/TestRunner.cs")
STATE = Path("project-state/PROJECT-STATE.md")


def replace_checked(path, old, new, minimum=1):
    text = path.read_text(encoding="utf-8")
    if new in text and old not in text:
        print(f"ok    already patched: {path}")
        return
    hits = text.count(old)
    if hits < minimum:
        raise RuntimeError(f"{path}: expected at least {minimum} occurrence(s) of {old!r}, found {hits}")
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"edit  {path}: {hits} replacement(s)")


try:
    replace_checked(CSPROJ, "<Version>0.9.65</Version>", "<Version>0.9.66</Version>")
    replace_checked(VM, "Classroom Studio v0.9.65", "Classroom Studio v0.9.66")
    replace_checked(RUNNER, "<Version>0.9.65</Version>", "<Version>0.9.66</Version>", 20)
    replace_checked(RUNNER, "Classroom Studio v0.9.65", "Classroom Studio v0.9.66", 15)
    replace_checked(RUNNER, "csproj version is 0.9.65", "csproj version is 0.9.66", 2)
    replace_checked(RUNNER, "        var curMinor = 65;", "        var curMinor = 66;")
except RuntimeError as exc:
    print("FAIL:", exc)
    sys.exit(1)

state = """# Classroom Studio — وضعیت زنده‌ی پروژه

> منبع حقیقت جاری پروژه؛ تاریخچه‌ی کامل در صفحه‌ی Notion پروژه نگهداری می‌شود.

## وضعیت لحظه‌ای — ۲۰۲۶-۰۹-۱۱

- خط ریلیز اپ: `0.9.66 / PLAN|2`
- مخزن: `pedrampedi81-dotcom/smc`
- شاخه‌ی ریلیز: `release/app-0.9.66`
- PR #26 با squash در `main` ادغام شد.
- merge commit مبنا: `837188161e5edb441802d9ff0d5ebdff58fb9cf2`.
- Issue #25 با `state_reason=completed` بسته شد.
- head نهایی پیش از merge: `8b4d049406eb7532b2d23fdc993551ba675ae94b`.
- Windows app CI نهایی: run `34574394673` / job `103183453164` — success.

## پذیرش تثبیت‌شده

- hotfix سخت‌افزاری `h6-v2` روی Pico واقعی پذیرفته شد.
- GP4/Num Lock وسط `KTEXT` توقف فوری می‌دهد.
- پایان طبیعی finite plan موتور را به Idle برمی‌گرداند و اجرای بعدی با یک فشار شروع می‌شود.
- لاگ `pico-console-20260911-095058.txt` هیچ `plan: run error` یا `PlanAbort isn't defined` نداشت.
- PONG پذیرفته‌شده: `role=brain+keyboard+light`, `arm=promicro`, `planapi=3`, `engine=split`, `framing=1`, `baud=57600`, `lagmax=2`.
- شمارنده‌های خرابی `cksum=0`, `noframe=0`, `sentjumps=0`, `partial=0` بودند؛ `dropped` coalescing عمدی تحت back-pressure است.
- همه‌ی gateهای نهایی compile، golden، compiler، sim2، sim3، hashes، sensitive-guard و Windows build-test سبز شدند.
- runtime سه‌فایلی در بودجه است: core ≤ 26,000، motion ≤ 15,000 و typing ≤ 5,000 بایت.
- exporter، child planهای بازگشتی و runtime سه‌فایلی را با transaction کامل stage/publish/rollback منتشر می‌کند.

## سیاست نسخه‌ی ریلیز

- نسخه‌ی اپ در این PR از `0.9.65` به `0.9.66` می‌رود.
- Pico firmware bundle عمداً روی baseline پذیرفته‌شده‌ی `0.9.64f` می‌ماند.
- Pro Micro عمداً روی baseline پذیرفته‌شده‌ی `2.5` می‌ماند.
- هیچ فایل کلید واقعی، HEX حساس یا backup وارد مخزن نمی‌شود.

## گیت ادغام PR ریلیز

1. app build بدون خطا.
2. TestRunner با `0 failed`.
3. تمام checkهای PLAN2 و sensitive guard سبز روی head نهایی.
4. merge فقط از مسیر PR؛ هیچ push مستقیمی به `main`.

## بعد از ریلیز اپ

- در صورت نیاز، candidate artifact رسمی از نام قدیمی `h5` به خط پذیرفته‌شده‌ی `h6` ارتقا داده شود؛ این کار از bump اپ جدا نگه داشته می‌شود.
"""
STATE.write_text(state, encoding="utf-8")

exporter = EXPORTER.read_text(encoding="utf-8")
runner = RUNNER.read_text(encoding="utf-8")
if f'BundleVersion = "{BUNDLE}"' not in exporter:
    print("FAIL: Pico BundleVersion moved from accepted 0.9.64f")
    sys.exit(1)
if "<Version>0.9.66</Version>" not in CSPROJ.read_text(encoding="utf-8"):
    print("FAIL: csproj app version did not reach 0.9.66")
    sys.exit(1)
if "Classroom Studio v0.9.66" not in VM.read_text(encoding="utf-8"):
    print("FAIL: app banner did not reach 0.9.66")
    sys.exit(1)
if "        var curMinor = 66;" not in runner or "        var curBundleMinor = 64;" not in runner:
    print("FAIL: TestRunner app/bundle meta pins are wrong")
    sys.exit(1)

app_pins = set()
bundle_pins = set()
for line in runner.splitlines():
    is_bundle = "BundleVersion" in line
    if "<Version>0.9." not in line and "Classroom Studio v0.9." not in line and not is_bundle:
        continue
    for match in re.finditer(r"0\.9\.(\d+)", line):
        i = match.start()
        is_label = i > 0 and line[i - 1] == "v" and match.end() < len(line) and line[match.end()] == ":"
        if not is_label:
            (bundle_pins if is_bundle else app_pins).add(int(match.group(1)))
if app_pins != {66} or bundle_pins != {64}:
    print(f"FAIL: pin families wrong: app={sorted(app_pins)} bundle={sorted(bundle_pins)}")
    sys.exit(1)

print("PASS: app 0.9.66; Pico bundle 0.9.64f; Pro Micro baseline 2.5")
