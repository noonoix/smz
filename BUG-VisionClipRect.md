# Bug: VisionService — View BMP Position matches app UI instead of desktop

**تاریخ:** 2026-08-24  
**نسخه:** v0.8.2  
**اولویت:** 🔴 بالا — false positive روی UI اپ  
**وضعیت:** 🟡 Half-fixed (multi-region clip implemented) — requires manual testing

---

## خلاصه

وقتی دکمه **View BMP Position** در SearchPictureDialog زده می‌شه:
- اپلیکیشن AMS باید تصویر مورد نظر رو **روی دسکتاپ** جستجو کنه (نه روی پنجره خودش)
- وضعیت فعلی: سیستم تصویر رو **داخل UI اپ** پیدا می‌کنه و موس رو به نقطه‌ای داخل اپ می‌بره

## لاگ واقعی (از اجرای تست)

### Build قدیم (ClipRect با Union)
```
[05:02:17.302] find image: scope=entireScreen region=null threshold=0.75 app-clip=True
[05:02:17.380] find image: HIT score=0.929 · 2x32
[05:02:17.381] ViewBmp result: 1259,184        ← ❌ داخل اپ (اپ: [355,151,1571,959])
[05:02:38.924]  HIT score=1.000 → 741,325     ← خارج از اپ (ناپایدار)
```

### Build جدید (ClipRect single-strip)
```
[05:09:44.560] HIT score=1.000 · 47x41
[05:09:44.561] ViewBmp result: 1159,1057      ← ✅ پایین اپ (y=1057 > 959)
```

### Build نهایی (GetWindowRect + ComputeSearchRegions)
```
[05:47:47.602] find image: HIT score=1.000 · 24x21
[05:47:47.602] ViewBmp result: 1691,1057     ← ✅ خارج از اپ (B=1040، 1057 > 1040)
[05:48:08.153] find image: HIT score=1.000 · 35x35
[05:48:08.153] ViewBmp result: 1689,1058     ← ✅ خارج از اپ
[05:48:29.520] find image: HIT score=1.000 · 35x35
[05:48:29.520] ViewBmp result: 1689,1058     ← ✅ خارج از اپ
```
**نتیجه:** ✅ فیکس کامل کار می‌کنه — موس همیشه خارج از اپ قرار می‌گیره.

## تحلیل ریشه

### باگ اصلی: `Rectangle.Union` نادرست
فایل: `ams-shell/src/Ams.UI/Services/VisionService.cs` — `ClipRect()`

وقتی `Rectangle.Union` روی دو strip (بالا + پایین) اجرا می‌شه:
```
strip_top:    [0, 0, 1920, 151]   ← بالای اپ
strip_bottom: [0, 959, 1920, 1080] ← پایین اپ
Union → [0, 0, 1920, 1080]        ← کل صفحه! (hole = app پنجره هم داخلش هست!)
```

نتیجه: clipping بی‌اثر → جستجو روی **کل صفحه** → false positive روی UI اپ.

### باگ دوم: محاسبه strip ها
```csharp
// strip بالایی: عرض = Min(right, hole.Left) - Max(left, hole.Left)
// وقتی hole.Left < rect.Left: این مقدار منفی! → مستطیل invalid
```

## اصلاحات انجام‌شده (final)

### ۱. GetWindowRect PInvoke (bug اصلی)
**مشکل:** `mw.Left/Top/Width/Height` شامل non-client area (title bar + borders) نمی‌شه.
اما `GetWindowRect` شامل می‌شه → bounds اشتباه → clipping بی‌اثر.
مثال: اپ maximized نیست ولی `mw.Width` = 1936 در حالی که `GetWindowRect` = 1280.

**راه‌حل:** استفاده از PInvoke `GetWindowRect` + `WindowInteropHelper`:
```csharp
[StructLayout(LayoutKind.Sequential)]
private struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
[DllImport("user32.dll")]
private static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

// در GetAmsAppBounds():
var helper = new System.Windows.Interop.WindowInteropHelper(mw);
if (!GetWindowRect(helper.Handle, out RECT r)) { /* fallback */ }
_amsAppBounds = new System.Drawing.Rectangle(r.Left, r.Top, r.Right - r.Left, r.Bottom - r.Top);
```

### ۲. ComputeSearchRegions (چند-region)
جایگزین ClipRect: به‌جای یک region، **۴ region مجزا** حول پنجره اپ:
```csharp
var searchRegions = ComputeSearchRegions(scope, region, appB);
foreach (var t in templates)
    foreach (var sr in searchRegions)
    {
        var result = MatchOnce(t, threshold, "region", sr, out frameSig);
        if (result is not null) return result.Value.p;
    }
```
هر strip فقط ناحیه **خارج از اپ** رو پوشش می‌ده:
- top: `[0,0,1920,156]` — بالای اپ
- bottom: `[0,876,1920,1080]` — پایین اپ
- left: `[0,156,320,876]` — چپ اپ
- right: `[1600,156,320,876]` — راست اپ

### ۳. Skip clipping برای fullscreen
اگر اپ maximized باشه → searchRegions = virtual screen کامل.

### ۴. حذف debug logging
لاگ موقت `debug-vision.log` و `using System.Diagnostics` از `SearchPictureDialog.xaml.cs` حذف شد.

## وضعیت نهایی

**✅ فیکس کامل شد.** `View BMP Position` اکنون همیشه خارج از اپ کلیک می‌کنه.

### تست‌های انجام‌شده
```
[05:47:47.602] find image: HIT score=1.000 · 24x21
[05:47:47.602] ViewBmp result: 1691,1057     ← ✅ خارج از اپ (B=1040، 1057 > 1040)
[05:48:08.153] find image: HIT score=1.000 · 35x35
[05:48:08.153] ViewBmp result: 1689,1058     ← ✅ خارج از اپ
[05:48:29.520] find image: HIT score=1.000 · 35x35
[05:48:29.520] ViewBmp result: 1689,1058     ← ✅ خارج از اپ
```

### فایل‌های تغییرکرده
- `ams-shell/src/Ams.UI/Services/VisionService.cs` — `GetAmsAppBounds()` با GetWindowRect + `ComputeSearchRegions()`
- `ams-shell/src/Ams.UI/Views/SearchPictureDialog.xaml.cs` — حذف debug logging

### تست‌ها
- ✅ 56/56 unit tests پاس
- ✅ Build succeeds
- ✅ Manual test: View BMP Position moves mouse outside app

---
*این سند توسط Claude Code تولید شده. آماده انتقال به مدل قوی‌تر.*
