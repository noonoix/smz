# Classroom Studio — تصویر کلی پروژه (PROJECT STATE)

> **این فایل مرجع زنده‌ی پروژه است. قانون: بعد از هر تغییر مهم، Notion AI این فایل را در همین ریپو به‌روز می‌کند.**
> در جلسه‌ی جدید با Notion AI کافی است بگویید: «از ریپوی pedrampedi81-dotcom/smc فایل project-state/PROJECT-STATE.md را بخوان» تا تصویر کلی برگردد.
> آخرین به‌روزرسانی: 2026-09-07 · نسخه‌ی در کار: **v0.9.58**

---

## ۱) پروژه چیست

**Classroom Studio** — اپ WPF (net8.0-windows، WPF-UI) برای اتوماسیون کلاس/امتحان: ساخت سناریوهای مرحله‌ای (موس، کیبورد، تصویر، صدا، نور) و اجرایشان روی سخت‌افزار.

معماری سه‌لایه:
1. **اپ دسکتاپ** `ClassroomStudio.exe` (سورس: `ams-shell/src/Ams.UI/`، تست‌ها: `tests/TestRunner.cs`)
2. **پل پایتون** `bridge/bridge.py` + `ams_serial.py` + `ams_crypto.py` (کانال رمزنگاری‌شده AES-128، قاب E|n|hex، PSK از ams_key.json یا env AMS_PSK)
3. **بردها**: Raspberry Pi Pico = مغز (کیبورد HID + سنسور نور BH1750 + هاب فرمان) · Arduino Pro Micro = بازو (موس + صدا) — Pico از طریق UART به Pro Micro فرمان پاس می‌دهد

## ۲) وضعیت لحظه‌ای (2026-09-07)

- آخرین release بررسی‌شده: **v0.9.58** — کیپد و self-containment اعمال شده، ولی با **۳ تست قرمز** ساخته شد (BundleVersion هنوز 0.9.57 مانده + دو تست vein) → **قابل انتشار نیست تا سبز شود**
- فیکس‌لیست کامل v0.9.58: `project-state/CLAUDE-IMPLEMENT-v0.9.58.md` را به Claude Code بدهید
- **باگ مهم پیدا و فیکس‌شده توسط Notion AI (کامیت 459e24dc):** `bridge.py` فاقد `import os` بود → هر Connect روی هر سیستمی با NameError می‌مرد (ریشه‌ی محتملِ وصل‌نشدن روی سیستم جدید)
- CI روی GitHub Actions فعال است (رانر ویندوزی رایگان)؛ ران‌های ۱ تا ۵ قرمز بودند — ریشه‌ها: باگ import os + قدم smoke مبتنی بر پروسه که روی رانر ناپایدار بود (race/هنگ) → در CI v5 با چک‌های قطعی جایگزین شد
- **منتظر:** نتیجه‌ی ران بعدی (سبز → Release با زیپ ظاهر می‌شود / قرمز → Issue با نام قدم شکست)

## ۳) ریپو و چرخه‌ی CI

- ریپو: `github.com/pedrampedi81-dotcom/smc` (private)
- هر push به `main` → بیلد Release + py_compile پشته‌ی bridge + چک import + TestRunner
- **سبز → Release با `Classroom-Studio-release.zip` + sha256 + لاگ تست · قرمز → Issue با نام قدم شکست‌خورده**
- قانون طلایی: **publish فقط با `0 failed`** — بدون استثنا
- نقشه‌ی کار: Claude Code فقط کد می‌نویسد و push می‌کند؛ Notion AI نتیجه را می‌خواند، بازرسی می‌کند، و برای باگ‌های کوچک مستقیم پچ push می‌کند
- ⚠️ ران‌ها را در تب Actions دستی Cancel نکنید — گزارش‌دهی issue را قاتی می‌کند

## ۴) سخت‌افزار — نقشه‌ی سیم‌کشی v6 (مرجع)

| سیگنال | Pico | از طریق | مقصد |
|---|---|---|---|
| UART TX | GP16 (پین 21) | BSS138 LV1/HV1 | Pro Micro D0/RXI (پین 23) |
| UART RX | GP17 (پین 22) | BSS138 LV2/HV2 | Pro Micro D1/TXO (پین 24) |
| I2C SDA | GP20 (پین 26) | مستقیم | BH1750 SDA |
| I2C SCL | GP21 (پین 27) | مستقیم | BH1750 SCL |
| 3V3 | پین 36 | — | LV شیفتر + VCC سنسور |
| GND | پین 23/38 | — | مشترک همه‌جا |
| BTN1 (key1 کیپد) | GP2 | خازن 100nF | GND (کامن کیپد) |
| BTN2 (key2 کیپد) | GP3 | خازن 100nF | GND |
| key3/key4 | GP4/GP5 | — | رزرو |
| صدا (TIP جک) | — | 10µF + بایاس 10k/10k + 1k | Pro Micro A0/PF7 (پین 8) |

- شیفتر: BSS138 چهارکاناله، LV=3.3V / HV=5V · Pro Micro: VCC=5V، RAW=NC
- دو کابل USB: Pico و Pro Micro جداگانه به سیستم
- پورت‌ها روی سیستم اصلی: **COM17 = Pro Micro** (04D8:000B) · **COM3 = کنسول Pico · COM5 = data پیکو** (برنامه باید به data وصل شود؛ bridge با PING خودش پیدایش می‌کند)
- BH1750: ADDR→GND یعنی آدرس 0x23

## ۵) پروتکل سریال (خطی، 115200 8N1)

- `PING` → `OK|PONG|pico-light <ver>|role=brain+keyboard+light|arm=promicro`
- `LCAL|ms` → `OK|LCAL|min=..|max=..|avg=..` (دکمه‌ی Calibrate)
- `WLUX|lo,hi,stableMs,timeoutMs,mode` → `OK|WLUX|lux=..` یا `ERR|TIMEOUT|WLUX`
- `TRGLUX|...` → `EVT|TRGLUX|...` (کلید را خود برد می‌زند)
- `WSND|thr,minMs,timeout` / `TRGSND|...` (روی Pro Micro)
- `MMOVE|x,y,abs,human` · `MWHEEL|delta` · `MCLICK|...` · `HALT` / `BYE`
- پیشوندهای پاس‌به‌بازو: MMOVE MCLICK MWHEEL MDOWN MUP SETRES WSND TRGSND SCAL

## ۶) فرم‌ور پیکو (خروجی File → Export Pico Firmware)

- چهار فایل روی درایو `CIRCUITPY`: `code.py` + `boot.py` + `pico-calibration.json` + `README-FLASH.md` و پوشه‌ی `lib/adafruit_hid`
- CircuitPython 10.3.0 روی برد کاربر نصب است
- **نام فایل حتماً باید `code.py` باشد** (داستان copy.py — CircuitPython فقط code.py/code.txt را اجرا می‌کند)
- `boot.py` دو سریال می‌سازد: console (REPL/خطاها) + data (پروتکل) — دو COM دیدن یعنی سالم است
- `lux-test-v2.py` (در همین پوشه‌ی project-state) = تست مستقل سنسور با کیپد: key1=توقف، key2=مکث/ادامه
- توقف صحیح اسکریپت: جدا/وصل کردن برد یا Ctrl+C در کنسول — نه حذف فایل وسط اجرا

## ۷) پروفایل نور اندازه‌گیری‌شده (اتاق کاربر، PC-13458)

- محیط: 55–59 لوکس · روشن کامل (فلش/تست): پیک ۴۰۳۶ · پوشیده: ۲–۶ · jitter میان‌رده ۳۰–۹۵ (نشت نور اتاق → کلاهک تاریک لازم)
- وضعیت‌های پیشنهادی: روشن مرکز ۴۰۰۰ تلورانس ۱۵۰۰ · تاریک مرکز ۵ تلورانس ۲۰ · dead zone ≥ ۵۰ لوکس
- بازه‌ی پیش‌فرض ۱۲۰۰–۱۳۰۰ با این اتاق نمی‌خواند — همیشه Calibrate زنده بزنید

## ۸) کیپد (تصمیم نهایی کاربر)

- کیپد فلت ۱×۴ (۵ سیم: کامن + ۴ کلید) — کامن→GND، key1→GP2، key2→GP3، key3/4→GP4/GP5
- **نگاشت نهایی: key1 → Num Lock = اجرا/توقف · key2 → Scroll Lock = مکث/ادامه**
- فرم‌ور: digitalio + Pull.UP + دیبانس ۴۰ms، لبه‌ی فشردن، پول حتی داخل حلقه‌ی WLUX
- اپ: GlobalHotkeyService علاوه بر هات‌کی‌های کاربر همیشه 0x90/0x91 را هم ثبت می‌کند؛ Options پیش‌فرض Num Lock/Scroll Lock (قابل تغییر)
- پیاده‌سازی در DLL v0.9.58 تأیید شد (NUM_LOCK/SCROLL_LOCK/GP2/GP3 هست) — تست‌هایش در فیکس‌لیست مانده

## ۹) اقلام باز (به ترتیب اولویت)

1. **فیکس‌لیست v0.9.58** → `project-state/CLAUDE-IMPLEMENT-v0.9.58.md` به Claude Code (BundleVersion، دو تست vein، assertionهای کیپد+wildcard csproj+متا، حذف __pycache__ از زیپ)
2. نتیجه‌ی ران CI بعدی را چک کنم (Notion AI)
3. روی سخت‌افزار: هود تاریک → Connect به پورت data پیکو → Calibrate → `test-light-sensor.amsj` → `test-board-v6.amsj` (تست ۲ «arm keyboard ok» تعیین‌کننده‌ی مسیر UART است)
4. تست دستی روی ویندوز: auto-fill ۲۰ کیبورد، پنل تنظیمات داخلی، next/else چسبیده به رگ، tooltip زیر آیکون
5. بکلاگ: ایمپورتر AMK (daroon1)، موارد بصری v0.9.46-52، زیرصفحه‌ی pin-dictionary v3→v5

## ۱۰) قوانین طلایی (از درس‌های این جلسه)

- **هیچ release با تست قرمز منتشر نمی‌شود** — هزینه‌اش را دیدیم
- پین‌های نسخه در TestRunner هر ریلیز بامپ می‌شوند + تست مِتا جلوی فراموشی را می‌گیرد
- bridge.py: py_compile + import-check در CI، چون NameError را کامپایلر نمی‌گیرد
- رشته‌ی C# حاوی بک‌اسلش حتماً verbatim (`@"…"`)
- سایه‌زدن `e` در foreach کنار RoutedEventArgs ممنوع
- مسیرها همیشه نسبت به exe؛ تنظیماتِ ناموجود → خودکار AUTO/پیش‌فرض (self-healing)
- اسکریپت‌های بزرگ با heredoc و بعد `ls -la` تأیید
- پاکسازی تاریخچه COM فقط برای خانواده‌های مجاز و با بکاپ

## ۱۱) محیط کاربر

- سیستم اصلی: PC-13458 · سیستم دوم (تست جابه‌جایی): پورت COM4
- پوشه‌ی پایتون قدیمی: `C:\Users\wasteland\Documents\ams\pc` (از v0.9.57 دیگر لازم نیست — پشته bundled است)
- Caterina.hex، Sketchbook و boards.txt در مسیرهای شناخته‌شده‌ی قبلی
- Notion: صفحه‌ی پروژه «Classroom Studio — پروژه ۲» (id: 1268c638-fe00-44f8-a9c0-eda4124eae22)

---
*این سند هر بار که تغییر معناداری رخ دهد (نسخه‌ی جدید، تصمیم سخت‌افزاری، باگ ریشه‌ای) به‌روزرسانی می‌شود.*
