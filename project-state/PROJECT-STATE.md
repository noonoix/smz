# Classroom Studio — وضعیت زنده‌ی پروژه

> این سند، منبع حقیقت جاری پروژه است. بعد از هر نسخه به‌روز می‌شود.
> برگه‌ی Notion («Classroom Studio — پروژه ۲») تاریخچه‌ی کامل جلسات را دارد؛ این فایل وضعیت لحظه‌ای است.

## وضعیت لحظه‌ای — ۲۰۲۶-۰۹-۰۸ (به‌روزرسانی چهارم)

**مبنای فعلی: `main` @ v0.9.60 — CI سبز (`ci-16`: ۶۷۶ پاس / ۰ فیل) + پچ تجمیع v0.9.60**

- ریپو: `pedrampedi81-dotcom/smc` (private) · هر push سبز ← Release خودکار (زیپ + sha256 + لاگ) · هر قرمز ← Issue با خطوط FAIL
- آخرین Release قبل از این نسخه: **ci-16** (676/0) روی commit `a004df45` (دکمه‌ی کپی لاگ)
- آخرین نسخه‌ی منسوج: **v0.9.60 — firmware consolidation + transport hardening**

## v0.9.60 چه چیزی را یکجا می‌کند

قرارداد نهایی سخت‌افزار (مصوب ۰۰:۱۷ بامداد ۰۹-۰۸) که قبلاً فقط به‌صورت فایل standalone دست‌آزمایی شده بود (0.9.59h/k/m/n)، حالا وارد سورس و ژنراتور شد:

1. **فرم‌ور پیکو (`PicoFirmwareExporter.CodeTemplate`)** — بازنویسی hardened:
   - سنسور BH1750 **اختیاری** است؛ بدون سنسور بوت و `PING` کار می‌کند و `WLUX`/`TRGLUX`/`LCAL` ← `ERR|NOSENSOR` (رفع مرگ خاموش بوت با سیم شل‌شده)
   - بافر سریال **بایتی و کران‌دار** به‌جای الحاق رشته‌ای (رفع خردشدن heap و MemoryError)
   - **پمپ دائمی بازو** در هر تکرار حلقه و داخل انتظارها: EVTهای پرو میکرو زنده به PC می‌رسند و بافر TX کوچک بازو هرگز پر نمی‌شود (رفع زنجیره‌ی مرگ ۲۲:۲۲)
   - فرمان‌های موس **fire-and-ack** (فوروارد + پاسخ فوری) تا مسیرهای متراکم انسانی نرم بمانند؛ صدا/SETRES همچنان پاسخ واقعی بازو را منتظر می‌مانند
   - **کیبورد همیشه روی پیکو**: هر دو envelope ‏`KBDPICO|` و `KBDARM|` محلی مصرف می‌شوند؛ پرو میکرو هرگز تایپ نمی‌کند
   - **کیپد ثابت** مستقل از Options: ‏GP4→GND = Num Lock = Start/Stop · ‏GP3→GND = Scroll Lock = Pause/Resume (هم موتور standalone و هم HID به PC)
   - `AUTOSTART = False` پیش‌فرض: کپی/بوت code.py ماکرو را خودکار شروع نمی‌کند؛ موتور standalone تا ۳ ثانیه بعد از آخرین فرمان host ساکت است (ضد اجرای دوبل)
   - نگهبان **never-die** دور هر خط و کل حلقه (Ctrl+C همچنان کار می‌کند — Exception نیست)
2. **bridge.py** — خروجی never-die با UTF-8 اجباری (`reconfigure(encoding="utf-8", errors="replace")`) + فالبک `ensure_ascii=True` در emit؛ رفع کرش cp1252 هنگام **گزارش** خطا که خطای واقعی را پنهان می‌کرد
3. **PythonBoardBridge.cs** — `StandardOutputEncoding`/`StandardErrorEncoding = UTF-8` + `PYTHONIOENCODING=utf-8`؛ لاگ فارسی دیگر mojibake نیست
4. **UI** — `SelectionMode="Extended"` برای لاگ سریال (کپی خطوط انتخاب‌شده با Ctrl/Shift واقعاً کار می‌کند)
5. **stableSec اعشاری end-to-end** — `0.5` → ‏`WLUX|...,500,...` · خلاصه‌ی ردیف `0.5s` را نشان می‌دهد (نه int گردشده) · پارس دیالوگ مستقل از locale ویندوز (InvariantCulture + فالبک محلی)

نسخه‌ها: csproj + بنر + `BundleVersion` = **0.9.60** · نگهبان مِتای TestRunner: `curMinor = 60` · گام ۵۸ تست با ۱۵ assertion تازه

## معماری بردها (قرارداد قطعی)

| برد | نقش | پین‌ها |
| --- | --- | --- |
| Raspberry Pi Pico | مغز: کیبورد HID + سنسور نور BH1750 + موتور ماکرو standalone | UART0: GP16=TX ← GP17=RX (BSS138) · I2C: SDA=GP20 / SCL=GP21 (0x23) · کیپد: GP4=Start/Stop · GP3=Pause/Resume |
| Arduino Pro Micro (fw 1.7) | بازو: فقط موس + سنسور صدا | A0 = سنسور صدا · رم ۸۸٪ / فلش ۸۱٪ — فلش ISP با `isp_flash_app.py` انجام شد |

- مسیر عملیاتی همیشه از پیکو می‌گذرد؛ اتصال مستقیم USB به بازو فقط برای سرویس/تشخیص است
- `PING` روی پیکو: `OK|PONG|pico-light 0.9.60|role=brain+keyboard+light|arm=promicro`
- پل bridge اول مغز پیکو را پروب می‌کند (متن‌باز، بدون ams_key.json)؛ نبود ← BoardLink رمزشده برای اتصال مستقیم به بازو

## CI/CD

- ورک‌فلو v5.2: `py_compile` روی bridge.py + تست رفتاری `tools/test_bridge_pico.py` + build جداگانه‌ی TestRunner + تست‌ها با خروجی کامل (`2>&1`) · فقط ۰ فیل Release می‌سازد · push فقط-مستنداتی نادیده گرفته می‌شود
- دارون‌وابسته‌ها روی CI تمیز SKIP می‌شوند (طراحی‌شده)

## قدم بعدی

1. **تست سخت‌افزار v0.9.60:** Export Pico Firmware از اپ buildشده ← کپی روی CIRCUITPY ← `PING` باید `pico-light 0.9.60` بدهد ← تست موس از مسیر پیکو←بازو (باید نرم بماند — پمپ دائمی) ← تست کیپد GP4/GP3 ← تست بوت بدون سنسور
2. تست صدا: یک‌بار سکوت + یک‌بار صدای بلند Calibrate ← «کپی کل لاگ» ← تفکیک ۱۱–۱۲
3. بکلاگ: ایمپورتر AMK (دارون۱) · موارد بصری v0.9.46–52 · کاندیدای fw 1.8 بازو: رهاکردن پاسخ Serial1 وقتی TX پر است

## قواعد ثابت (خلاصه)

- هرگز selective merge نه — کل درخت جایگزین می‌شود · بلوک build اجباری + خروجی تازه‌ی TestRunner
- اول شبیه‌سازی Python، بعد C# · داده قبل از حدس
- هر نسخه: بنر + csproj + سند docs + ورودی MEMORY.md + نگهبان نسخه در TestRunner
- آینه‌ی گیت‌هاب برای هر مصنوع (sim/ · uploads/ · tools/)
