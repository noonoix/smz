# AMS — Step Open File (openFile)

**نسخه:** v0.1  
**پروژه:** Arduino Macro Studio — `ams-wpf-shell-v0.6`  
**فایل مبدأ:** `src/Ams.UI/Services/RunEngine.cs` (خطوط 80–97)  
**تعریف:** `src/Ams.UI/Models/StepDefinitions.cs:227`

---

## ۱. معماری

`openFile` تنها قدمی است که **کاملاً PC-side** اجرا می‌شود — هیچ فرمانی به برد آردوینو ارسال نمی‌گردد. مستقیماً از `Process.Start` ویندوز استفاده می‌کند.

```
┌─────────────────────────────────────────────────────┐
│              Run Engine                             │
│  openFile step                                     │
│       │                                            │
│       ▼                                            │
│  PropEx.GetString(s.Props, "path")                 │
│       │                                            │
│       ▼                                            │
│  File.Exists(p) ? → Process.Start(psi)             │
│  ✗  → لاگ: "not found — skipped"                   │
└─────────────────────────────────────────────────────┘
```

---

## ۲. ورودی‌ها (Properties)

| پروپرتی | نوع | پیش‌فرض | توضیح |
|---|---|---|---|
| `path` | `string` | — | مسیر کامل فایل/برنامه برای باز کردن |
| `args` | `string` | `null` | آرگومان‌های خط فرمان (اختیاری) |
| `windowState` | `enum` | `"normal"` | حالت پنجره: `normal` / `maximized` / `minimized` |

---

## ۳. جریان اجرا (Execution Flow)

```csharp
// 1. استخراج مسیر
var p = PropEx.GetString(s.Props, "path");

// 2. اعتبارسنجی
if (string.IsNullOrWhiteSpace(p))
    → لاگ: "openFile: empty path — skipped"
    → break (رد می‌شود)

if (!File.Exists(p))
    → لاگ: $"openFile: not found: {p} — skipped"
    → break (رد می‌شود)

// 3. ساخت ProcessStartInfo
var psi = new ProcessStartInfo(p) { UseShellExecute = true };

// 4. آرگومان‌ها (اختیاری)
var args = PropEx.GetString(s.Props, "args");
if (!string.IsNullOrWhiteSpace(args))
    psi.Arguments = args;

// 5. حالت پنجره
psi.WindowStyle = windowState switch
{
    "maximized"   => ProcessWindowStyle.Maximized,
    "minimized"   => ProcessWindowStyle.Minimized,
    _             => ProcessWindowStyle.Normal,
};

// 6. اجرا
Process.Start(psi);
```

---

## ۴. رفتارهای مرزی

| وضعیت | نتیجه |
|---|---|
| `path` خالی یا فقط فاصله | ✅ skip — لاگ ثبت می‌شود |
| فایل وجود ندارد | ✅ skip — لاگ با مسیر ثبت می‌شود |
| `args` خالی | ✅ بدون آرگومان اجرا می‌شود |
| `windowState` نامعتبر | ✅ fallback به `normal` |
| فایل بازشو غیرقابل اجرا (مثل `.txt` روی system32) | بستگی به shell association — ویندوز خود تصمیم می‌گیرد |

---

## ۵. تفاوت با سایر قدم‌ها

| قدم | اجرا در | مکانیسم |
|---|---|---|
| `mouseMove` | برد | `MMOVE\|x,y,abs` → آردوینو |
| `mouseClick` | برد | `MCLICK\|button,clicks` → آردوینو |
| `typeText` | برد | `KTEXT\|hmin,hmax,text` → آردوینو |
| `waitForSound` | برد | `WSND\|thr,min,timeout` → آردوینو |
| **`openFile`** | **PC** | **`Process.Start` — بدون برد** |
| **`findImage`** | **PC** | **GDI + NCC — بدون برد** |
| `delay` | PC | `Task.Delay` — بدون برد |
| `forLoop` | PC | حلقه C# — بدون برد |

---

## ۶. ردپا و حساسیت (Detection Surface)

### لایه‌های قابل شناسایی:

| لایه | توضیح | شدت |
|---|---|---|
| **Event Viewer** | `ProcessCreate` events در `Microsoft-Windows-Threat-Intelligence` یا `Sysmon` | 🔴 متوسط |
| **UIPI/Shell** | اگر فایل به‌درستی اجرا نشود، window error dialog ظاهر می‌شود | 🟡 کم |
| **CPU usage spike** | اجرای program ممکن است لحظه‌ای CPU را بالا ببرد | 🟢 کم |

### عوامل کاهندهٔ ریسک:

- `UseShellExecute = true` — از shell association استفاده می‌کند (مثلاً `.txt` → notepad.exe)
- `minimized` window state — پنجره بلافاصله minimized می‌شود
- delay پیش‌فرض 500ms — پس از openFile یک وقفه کوتاه وجود دارد

### مثال‌های کاربردی:

**باز کردن notepad با فایل:**
```json
{"type": "openFile", "props": {"path": "C:\\temp\\notes.txt"}}
```
→ ویندوز notepad را باز کرده و فایل را بارگذاری می‌کند.

**اجرای برنامه با آرگومان:**
```json
{"type": "openFile", "props": {"path": "C:\\Program Files\\App\\app.exe", "args": "--quiet", "windowState": "minimized"}}
```
→ برنامه در پس‌زمینه اجرا می‌شود.

---

## ۷. محدودیت‌ها

| محدودیت | توضیح | راهکار |
|---|---|---|
| **بدون پاسخ‌دهی** | `Process.Start` fire-and-forget — return value ندارد | برای تایید اجرای موفق نیاز به polling روی صفحه دارید |
| **وابسته به Shell** | `UseShellExecute=true` یعنی association فایل‌ها مهم است | مسیر کامل بدهید نه فقط نام |
| **مسیر نسبی** | از مسیر نسبی پشتیبانی نمی‌کند | همیشه path مطلق بدهید |
| **UAC Prompt** | اگر برنامه نیاز به admin دارد، prompt ظاهر می‌شود | از `runas` verb استفاده نکنید (حالا پشتیبانی نمی‌شود) |

---

## ۸. مقایسه با AMK

در AMK استاندارد، `OpenFile` یک قدم داخلی است. در AMS:
- ✅ از `PropEx` برای خواندن props استفاده می‌کند (سازگار با فرمت `.amsj`)
- ✅ validation path دارد (خروج راحت اگر فایل نباشد)
- ❌ هیچ wait/polling برای صبر کردن تا close شدن برنامه وجود ندارد
- ⚠️ هیچ event tracking برای UAC prompt وجود ندارد

---

*تولید شده توسط Claude Code — August 2026*
