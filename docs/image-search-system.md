# AMS Image Search — سیستم تشخیص تصویر

**نسخه:** v0.7.6  
**پروژه:** Arduino Macro Studio — `ams-wpf-shell-v0.6`  
**فایل اصلی:** `src/Ams.UI/Services/VisionService.cs`

---

## ۱. معماری کلی

تشخیص تصویر کاملاً **PC-side** اجرا می‌شود — هیچ پردازشی روی برد آردوینو انجام نمی‌گیرد. فقط مختصات نقطهٔ یافت‌شده (X,Y) به برد ارسال می‌شود تا ماوس به آنجا حرکت کند.

```
┌─────────────────────────────────────────────┐
│               Run Engine                    │
│  FindImage step → VisionService.FindOnScreen│
│           ↓                                   │
│  Point? → click(x,y) → board                │
│  null   → timeout → continue                │
└─────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│              VisionService                  │
│  LoadTemplates → [Bitmap]                   │
│  FindOnScreen loop (120ms poll)             │
│    └→ MatchOnce per template (OR logic)     │
│         └→ GDI CopyFromScreen               │
│            └→ ToGray                        │
│               └→ MatchGray (NCC + integral) │
│                  └→ Coarse(3px) + Refine(1) │
└─────────────────────────────────────────────┘
```

---

## ۲. ورودی‌های هر قدم Find Image

| پروپرتی | نوع | پیش‌فرض | توضیح |
|---|---|---|---|
| `paths` | `string[]` | — | مسیرهای فایل‌های عکس template (OR logic) |
| `similarity` | `int %` | 75 | حداقل NCC threshold (1-100) |
| `scope` | `enum` | `entireScreen` | محدوده جستجو |
| `region` | `Rectangle?` | null | مختصات region (وقتی scope=region) |
| `timeoutValue` | `double` | 3 | مقدار timeout |
| `timeoutUnit` | `string` | `second` | واحد timeout (second/minute/hour) |
| `neverTimeout` | `bool` | false | true = polling بی‌نهایت |

---

## ۳. فرآیند جستجو — حلقهٔ اصلی

```csharp
while (true)
{
    ct.ThrowIfCancellationRequested();
    foreach (var t in templates)          // OR: هر template یک بار چک می‌شود
    {
        var hit = MatchOnce(t, threshold, scope, region);
        if (hit is not null) return hit;  // اولین match برگشت داده می‌شود
    }
    if (!neverTimeout && sw.Elapsed >= timeout) return null;
    Thread.Sleep(120);                    // cadence مشابه AMK
}
```

- **Polling cadence:** هر 120ms یک بار اسکرین‌شات جدید گرفته می‌شود.
- **توقف:** timeout رسیدن، یا cancellation requested، یا یافتن الگو.

---

## ۴. محدودهٔ جستجو (Scope)

| scope | منطقهٔ جستجو | استفاده |
|---|---|---|
| `entireScreen` | `VirtualScreen` (چند مانیتور) | جستجوی سراسری |
| `fromCursor` | 800×600 پیکسل حول مکان نشانگر | نزدیک‌ترین به cursor |
| `region` | مستطیل تعریف‌شده توسط کاربر | دقیق‌ترین، سریع‌ترین |

محدوده با `Rectangle.Intersect` روی `VirtualScreen` قیچی می‌شود تا از مرزهای صفحه خارج نشود.

---

## ۵. تبدیل به خاکستری (ToGray)

عکس‌ها ابتدا به `Format24bppRgb` نرمال‌سازی می‌شوند، سپس هر پیکسل به یک بایت خاکستری تبدیل می‌شود:

```csharp
gray = (byte)((R + G + B) / 3);   // میانگین ساده سه کانال
```

**دلیل:** محاسبات NCC روی فضای یک‌بعدی سریع‌تر و کم‌حافظه‌تر از RGB سه‌بعدی است.
**مزیت:** تغییرات رنگ جزئی (lighting variations) تأثیر کمتری دارند.

---

## ۶. الگوریتم تطبیق: NCC با Integral Image

### ۶.۱ محاسبهٔ میانگین و انحراف std هر پنجره

با استفاده از **Integral Image** (فرمول 4-corner):

```
sum(x,y,w,h) = II[y,x]   - II[y,x+w]   - II[y+h,x]   + II[y+h,x+w]
sumSq(x,y,w,h)= II2[y,x] - II2[y,x+w] - II2[y+h,x] + II2[y+h,x+w]
mean = sum / n
std  = sqrt(max(0, sumSq - n * mean²))
```

این محاسبه O(1) است — فقط 4 دسترسی حافظه‌ای برای هر پنجره.

### ۶.۲ Normalized Cross-Correlation

```
NCC = Σ((hay[i] - hMean) * (needle[i] - nMean)) / (stdHay * stdNeedle * n)
```

- دامنه NCC: [-1, 1]
- 1 = تطابق کامل
- < 0 = قرینه (الگوی وارونه)
- 0 = بدون همبستگی

**نقطهٔ cutoff:** `similarity% → threshold = similarity/100`

### ۶.۳ دو فاز جستجو

| فاز | گام | دامنه | توضیح |
|---|---|---|---|
| **Coarse** | 3 پیکسل | کل screen | یافتن بهترین حدس اولیه |
| **Refine** | 1 پیکسل | ±3 پیکسل اطراف best coarse | دقت زیرپیکسلی |

---

## ۷. پیوستگی: Coarse → Refine

```
best = null; bestScore = threshold
for y=0..hh step 3:
  for x=0..hw step 3:
    score = NCC(window)
    if score > bestScore: bestScore=score, best=(x,y)

# Refine
x0 = max(0, best.X-3), x1 = min(hw-nw, best.X+3)
y0 = max(0, best.Y-3), y1 = min(hh-nh, best.Y+3)
for y=y0..y1:
  for x=x0..x1:
    score = NCC(window)
    if score > bestScore: bestScore=score, best=(x,y)

return centerPoint(best) = (best.X + nw/2, best.Y + nh/2)
```

مرکز matched region به عنوان نقطهٔ کلیک ارسال می‌شود.

---

## ۸. رفتارهای مرزی

| وضعیت | نتیجه |
|---|---|
| Template بیشتر از screen | null فوری (قبل از اسکرین‌شات) |
| Template flat (همه‌پیکسل یکسان) | skip — std=0، NCC بی‌معنی |
| Region خارج از VirtualScreen | Intersect → خالی → null |
| timeoutMs = 0 و neverTimeout=true | polling تا ابد (تا manually stop) |
| timeoutMs = 0 و neverTimeout=false | فوری timeout → null |
| چند template: first match برمی‌گردد | OR logic — هر template که زودتر مچ شد |

---

## ۹. محدودیت‌ها و نکات عملی

| محدودیت | توضیح | راهکار |
|---|---|---|
| **Fullscreen Exclusive** | GDI تصویر سیاه می‌دهد | بازی را Borderless Windowed کنید |
| **Anti-cheat** | GDI اسکن نمی‌شود (EAC/BattlEye/Vanguard) | ✅ امن — اما policy anti-cheat ممکن است عوض شود |
| **Cursor روی الگو** | نشانگر ماوس در اسکرین‌شات دیده می‌شود | scope=fromCursor با cursor در مرکز، یا region دقیق |
| **تغییر مقیاس DPI** | DPI scaling >100% مختصات virtual screen را تغییر می‌دهد | region را با مقیاس DPI تطبیق دهید |
| **تغییر اندازه الگو** | NCC نسبت به scaling حساس است | template باید دقیقاً هم‌اندازه باشد |
| **چرخش الگو** | پشتیبانی نمی‌شود | template باید هم‌جهت باشد |
| **فریم‌گیری اطلاعات حساس** | اسکرین‌شات لحظه‌ای از همه‌چیز روی صفحه | region را محدود کنید |

---

## ۱۰. جریان داده (Data Flow)

```
StepNode.Props["paths"]       ──┐
StepNode.Props["similarity"]   ──┤── RunEngine.RunFindImageAsync()
StepNode.Props["searchScope"]  ──┤      ↓
StepNode.Props["timeoutValue"] ──┘── VisionService.FindOnScreen()
                                              ↓
                               ┌─ LoadTemplates() ──▶ Bitmap[] (dispose after)
                               │
                               └─ MatchOnce()
                                     │
                        ┌────────────┼────────────┐
                        ▼            ▼            ▼
                 GDI Capture    ToGray     MatchGray
                 (CopyFrom      (R+G+B)/3   (integral
                  Screen)                    NCC coarse
                                          + refine)
                        │
                        ▼
                 Point? center ──▶ RunEngine.click(x,y)
                 null ──▶ continue (or abort)
```

---

## ۱۱. نمونه مقادیر عملی

| سناریو | similarity | scope | timeout |
|---|---|---|---|
| پیدا کردن دکمهٔ Start | 80% | fromCursor | 5 ثانیه |
| پیدا کردن icon کنسول | 70% | region | 10 ثانیه |
| صبر برای لود شدن UI | 60% | entireScreen | 60 ثانیه |
| انتظار برای خطا (بدون timeout) | 75% | fromCursor | infinity |

---

*تولید شده توسط Claude Code — August 2026*
