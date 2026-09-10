# PlanExporter — فاز ۲ خط پرتابل (PLAN|1 روی فریم‌ور 0.9.64b)

**وضعیت:** برنچ `feat/plan-exporter-plan1` · v0.9.65 · ۲۰۲۶-۰۹-۱۰
**قاعده‌ی طلایی ۳:** اول شبیه‌سازی پایتون (`tools/plan_export_twin.py` + `sim/sim_plan_export.py` — **۵۴/۵۴ سبز** روی موتور واقعی gen-1)، بعد پورت C#.

## تصمیم (از برگه‌ی پروژه، ۱۰ سپتامبر)

تشخیص روی درایو ثابت کرد: زنجیره‌ی پیکو ← موتور پلن ← بازو ← HID روی خط `code64b` کاملاً سالم است؛ «پلنِ مرده» رد شد. تنها قید: موتور روی درایو فقط هدر `PLAN|1` و ۱۱ اپ نسل ۱ را می‌پذیرد (`PLAN, SCREEN, SPEED, RMOUSE, CLICK, TYPE, DELAY, LOOP, LOOPTIME, ENDLOOP, WLIGHT`)، در حالی که `plan_gen.py` نسل ۳ هدر `PLAN|2` می‌نویسد (خط 0.9.66 پارک‌شده — باگ باز دارد). **پس `PlanExporter.cs` برای خط 0.9.64b هدر `PLAN|1` می‌نویسد.**

## ماتریس ۲۳ اکشن × پورت

**کامپایل می‌شوند (۸):** `randomMousePosition` ← `RMOUSE` · `mouseMove` ← `RMOUSE|region=x,y,1,1` (منطقه‌ی ۱×۱ = همان حرکت انسانی قطعی به نقطه؛ موتور هر پاس `randint(x, x+0)=x` می‌کشد) · `mouseClick` ← `CLICK` · `typeText` ← `TYPE` (فقط ASCII) · `delay` ← `DELAY` · `forLoop` ← `LOOP/LOOPTIME…ENDLOOP` · `waitForLight` ← `WLIGHT` (ساده + مسلح) · `comment` ← `#`.

**مسدودکننده با نام استپ (۱۵، هرگز بی‌صدا حذف نمی‌شوند):** `findImage` (بینایی ماشین) · `waitForSound` (WSND نیست) · `keystroke`/`keyDown`/`keyUp` (KEY/KDOWN/KUP نیست — موتور فقط TEXT تایپ می‌کند) · `mouseScroll` (WHEEL نیست) · `label`/`gotoLabel` · `rawCommand` · `randomPackage` (RPKG) · `parallelGroup` (PGROUP) · `playAudio` · `playScript` (INCLUDE) · `runExe`/`openFile` (Win+R فقط روی gen-2) · نوع ناشناخته. سربت If/Else (`insertIfElse`) هم مسدود است (`IFLUX/ELSE/ENDIF` اپ‌های gen-2‌اند) — نشانگرهای Else/End If بلع می‌شوند تا خطای آبشاری «نشانگر سرگردان» نسازند، و مسدودکننده‌های تودرتو همچنان نام برده می‌شوند.

## جبران‌های gen-1 نسبت به plan_gen (مهم)

موتور gen-1 وقتی کلیدی نوشته نشود، پیش‌فرض‌های داخلی‌اش مکث‌های میانی (۱۲٪) و استراحت‌های بلند (۱۰۰۰–۵۰۰۰ms هر ۵–۱۲ حرکت) را **روشن** می‌گیرد — با پیش‌فرض‌های اپ فرق دارد. پس اکسپورتر همیشه صریح می‌نویسد: `mid=` همیشه (حتی `mid=0:0,0` = خاموش) و `idle=` همیشه (`idle=1,1:0,0` = خاموش) · `mouseMove` همیشه `idle=1,1:0,0` دارد (حرکت نقطه‌به‌نقطه هرگز استراحت بلند نمی‌کند).

## قراردادها (سخت)

- Play Options: `once` بدون قاب · `times N` ← `LOOP|N` · `timed` ← `LOOPTIME|seconds` دور کل پلن.
- Delay بعد از استپ دقیقاً معنای اپ: برای کانتینر **بعد از ENDLOOP** می‌نشیند.
- استپ‌های غیرفعال شمرده و رد می‌شوند (گزارش می‌شوند، حذف نمی‌شوند).
- خروجی قبل از نوشتن با خودِ موتور dogfood می‌شود (`ValidatePlan` ساختاری در C#؛ در سندباکس با پارسر واقعی `plan_engine.py`).
- `KeyboardBoard=promicro` و `human=false` و `typoChance` قدیمی = **FLAG** مستند (نه خطا، نه سکوت).

## فایل‌ها

| فایل | نقش |
| --- | --- |
| `tools/PlanExporter.cs.tpl` | منطق کامپایلر C# (قالب) |
| `tools/make_plan_exporter.py` | ژنراتور لنگردار: قالب + `firmware/code64b/plan_engine.py` ← `Services/PlanExporter.cs` (موتور از یک منبع واحد splice می‌شود) |
| `tools/plan_export_twin.py` | دوقلوی پایتونی (مرجع اعتبارسنجی) |
| `sim/sim_plan_export.py` | اثبات ۵۴/۰ روی موتور واقعی (پارس + اجرا با ctx ضبط‌کننده) |
| `tools/patch_plan_exporter_ui.py` | پچر لنگردار idempotent سیم‌بندی UI (منو + دستور + گام ۵۹ تست) |
| `tools/plan_exporter_test_step.cs.inc` / `plan_exporter_vm_command.cs.inc` | payloadهای پچر |
| `.github/workflows/apply-plan-exporter.yml` | ورک‌فلوی موقت (قبل از مرج حذف می‌شود) |
| `tools/patch_version_pins_0965.py` | ابزار بمپ ریلیز 0.9.65 (آماده؛ در همین برنچ اجرا **نشد** — قاعده‌ی PR #13/#16) |

## نسخه

این برنچ عمداً هیچ پین نسخه‌ای را دست نمی‌زند (الگوی اثبات‌شده‌ی PR #13/#16 — CI سبز می‌ماند). برچسب‌های assertion گام ۵۹ (`v0.9.65:`) به شکل label از اسکن نگهبان مستثنا‌اند. بمپ نهایی اپ به 0.9.65 هنگام ریلیز با `tools/patch_version_pins_0965.py` انجام می‌شود؛ چون قالب فریم‌ور دست‌نخورده است، `BundleVersion` صادقانه روی `0.9.64b` می‌ماند و نگهبان مِتا شکاف app/bundle را یاد می‌گیرد.

## بازتولید از صفر

```bash
python tools/make_plan_exporter.py .       # قالب + موتور ← Services/PlanExporter.cs
python sim/sim_plan_export.py              # ۵۴/۰ روی موتور واقعی
python tools/patch_plan_exporter_ui.py .   # سیم‌بندی UI + تست (idempotent)
```

## تست سخت‌افزاری (بعد از مرج و ریلیز)

۱) «File ← Export Pico Plan…» روی یک پلن موس+تایپ ← `plan.txt` + `plan_engine.py` روی CIRCUITPY (کنار `code.py` فعلی) ← بنر کنسول `pico-light 0.9.64b` و `plan: loaded N ops` ← Num Lock = اجرا.
۲) پلن با یک `keystroke` ← اکسپورت باید با پیام نام‌برده مسدود شود و هیچ فایلی ننویسد.
