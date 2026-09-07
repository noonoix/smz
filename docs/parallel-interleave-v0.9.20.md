# Parallel interleave + bridge discovery — v0.9.20

**تاریخ:** 2026-09-01
**نسخه:** v0.9.20
**وضعیت:** ✅ پیاده‌سازی شد — نیازمند build و تست روی ویندوز

---

## بخش اول — ریلیز به برد وصل نمی‌شد

### ریشه

`MainViewModel.CreateBridge()` فقط یک مسیر را چک می‌کرد:

```csharp
var bridgeScript = Path.Combine(AppContext.BaseDirectory, "bridge", "bridge.py");
```

`AppContext.BaseDirectory` = پوشه‌ی کنار exe. در خروجی build عادی
(`bin\Release\net8.0-windows\`) فایل csproj با `<CopyToOutputDirectory>` پوشه‌ی
`bridge\` را کنار exe کپی می‌کند و همه‌چیز کار می‌کند.

اما در زیپ ریلیزی که ساخته شده بود، exe روی `ams-shell\src\Ams.UI\` قرار داشت و
`bridge.py` در `ams-shell\bridge\` — یعنی **کنار exe پوشه‌ی `bridge\` وجود نداشت**.
نتیجه: `python <مسیرِ ناموجود> --pydir …` بلافاصله می‌میرد و چون اتصال هیچ‌وقت
fault نمی‌شد، اپ در وضعیت «Handshaking» معلق می‌ماند.

### رفع

۱. **کشف چندمسیره** — `PythonBoardBridge.BridgeScriptCandidates(baseDir)` به ترتیب:
   - `baseDir\bridge\bridge.py` (خروجی build استاندارد)
   - `baseDir\bridge.py` (پابلیش تخت)
   - تا ۴ سطح بالاتر: `<ancestor>\bridge\bridge.py`
     (exe داخل درخت سورس مثل `src\Ams.UI` → `ams-shell\bridge\bridge.py` پیدا می‌شود)

   اگر هیچ‌کدام نبود، **همه‌ی مسیرهای جست‌وجوشده در لاگ** چاپ می‌شود.

۲. **Fail-fast:** اگر پروسه‌ی python قبل از handshake بمیرد (`Exited`)، اتصال فوراً با
   خطای واضح شکست می‌خورد به‌جای معلق‌ماندن.

۳. **ریست وضعیت:** پس از اتصال ناموفق، bridge به `Disconnected` برمی‌گردد تا کلیک
   Connect بعدی واقعاً دوباره تلاش کند (قبلاً State روی Connecting گیر می‌کرد).

### بسته‌بندی ریلیز درست (برای Claude Code)

```powershell
dotnet publish ams-shell/src/Ams.UI/Ams.UI.csproj -c Release -o artifacts/publish
# تأیید کن: artifacts/publish/bridge/bridge.py باید وجود داشته باشد
# محتوای پوشه‌ی publish را زیپ کن — نه درخت سورس را
```

با کشف چندمسیره‌ی جدید حتی چیدمان نادرست هم کار می‌کند، ولی پابلیش درست همچنان لازم است
(فایل‌های .cs نباید در ریلیز باشند).

---

## بخش دوم — Parallel Group: موس حین تایپ می‌مرد

### استاندارد طلایی انسانی (از رکورد کاربر، ۵۷٫۸ ثانیه)

| معیار | انسان واقعی |
|---|---|
| تله‌پورت موس (>۴۰۰px در <۱۰۰ms) | **۰** |
| طولانی‌ترین سکون موس حین تایپ | **۱ ثانیه** |
| فاصله‌ی میان رویدادهای موس | میانه **۱۸ms** · p90 ۴۲ms · حداکثر ۲٫۷s |

### ریشه ۱ — انحصار کانال سریال توسط KTEXT

v0.9.15 در حالت موازی KTEXT را به تکه‌های **۸ کاراکتری** می‌شکست. برد برای هر کاراکتر
۸۰–۳۰۰ میلی‌ثانیه تاخیر انسانی اجرا می‌کند، پس هر تکه‌ی ۸ کاراکتری کانال تک‌سریال را
**۰٫۶ تا ۲٫۴ ثانیه** اشغال می‌کرد. قفل one-in-flight بریج یعنی MMOVEهای موس در این مدت
حتی ارسال هم نمی‌شدند → موس چند ثانیه فریز، بعد چند پیکسل، دوباره فریز —
الگوی رباتیِ «فریز–انفجار» که کاربر دید.

**رفع:** در حالت موازی هر op فقط **۱ کاراکتر** است (`ChunkKtextForParallel`) و
پس از هر op، مکث بین‌کلیدی **سمت اپ** با `NextRandom(hmin, hmax)` انجام می‌شود.
بدترین انسداد کانال = یک ضربه‌ی کلید؛ بین کلیدها کانال برای MMOVEهای موس آزاد است.
نتیجه مطابق الگوی انسانی: موس حین تایپ سریع بیشتر ساکن است ولی در فواصل، روان جریان دارد.

### ریشه ۲ — لنگر موقعیت موس (باگ «برگشتن به همان موقعیت»)

`HumanMoveToAsync` مسیر را از `Cursor.Position` (خوانش سیستم‌عامل) پلن می‌کرد. با
شاخه‌های موازی، خوانش OS می‌تواند از فرمان‌های صادرشده عقب بماند → مسیر بعدی از نقطه‌ی
**کهنه** شروع می‌شد و موس به‌چشم به محل شروع حرکت قبلی پرش می‌کرد.

**رفع:** `_mouseAnchor` در RunEngine — منبع واحد حقیقت برای «موس منطقاً کجاست»:

- در شروع run از `Cursor.Position` سینک می‌شود.
- هر فرمانِ جابه‌جاکننده‌ی موس آن را به‌روز می‌کند: waypoint به waypoint در حلقه‌ی موازی،
  پس از send_path موفق، در fallback، MMOVE خام، و clickRestoreCursor.
- پلن هر حرکت از لنگر شروع می‌شود، نه خوانش رقابتی OS.

---

## تست‌های رگرسیون — `tests/TestRunner.cs` گام ۲۱

| # | تست | انتظار |
|---|---|---|
| 21.1 | `ChunkKtextForParallel("KTEXT|80,300,hello!")` | ۶ op تک‌کاراکتری، هدر حفظ‌شده، بازسرjoin = متن اصلی |
| 21.2 | payload با کاما (`KTEXT|10,20,a,b`) | کاما کاراکتر لفظی است نه جداکننده |
| 21.3 | exe در عمق درخت سورس | `bridge\bridge.py` سطح‌ریپو با walk-up پیدا می‌شود |
| 21.4 | چیدمان پابلیش تخت | `bridge.py` کنار exe کاندید است |

---

## فایل‌های تغییریافته

| فایل | تغییر |
|---|---|
| `Services/RunEngine.cs` | `_mouseAnchor` + ۱-char KTEXT + `ChunkKtextForParallel` + `SendMmoveAbsAsync` (806 خط) |
| `Services/PythonBoardBridge.cs` | `BridgeScriptCandidates` + fail-fast + ریست وضعیت (326 خط) |
| `ViewModels/MainViewModel.cs` | `CreateBridge` چندمسیره + بنر v0.9.20 |
| `Ams.UI.csproj` | Version 0.9.20 |
| `tests/TestRunner.cs` | گام ۲۱ — ۶ assertion |
| `docs/parallel-interleave-v0.9.20.md` | همین سند |

`ScriptGenerator.cs` نیازی به تغییر ندارد — parallelGroup در اسکریپت تولیدی از قبل
مستنداً sequential است (کانال تک‌سریال، بدون رقابت).
