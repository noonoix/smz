# CHANGELOG — ۲۰۲۶-08-23

**پروژه:** `ams-wpf-shell-v0.6`  
**نسخه‌ها:** v0.7.7 + v0.7.8 + v0.7.9 + v0.8.0 + v0.8.1

---

## خلاصه روز

1. **v0.7.7** — دیالوگ جستجوی تصویر (`SearchPictureDialog`) + حفظ ۹ اقدام حفاظتی VisionService
2. **دارک تم** — بازنویسی رنگ‌های `SearchPictureDialog.xaml` با توکن‌های AMS (`Tokens.xaml`)
3. **v0.7.8** — Random Package (گام ۱۷ام) + Hold min/max + DelayMax + تست‌های ۴۴/۴۴
4. **v0.7.9** — Find Image dialog wire + real If/Else + rail icons رنگی + Warden hardening بازگردانده + ۴۸/۴۸ تست
5. **v0.8.0** — Accordion collapse/expand + scope lines نازک + Search Picture dialog fixes + ۵۳/۵۳ تست
6. **v0.8.1** — Region Picker double-click fix + RefreshPictureUi + Cut BMP preview واقعی + ۵۳/۵۳ تست

---

## v0.7.7 — Search Picture Dialog

### تغییرات اصلی
- دیالوگ AMK-style (`SearchPictureDialog`) جایگزین `StepDialog` برای نوع `findImage` شد
- **THUMBNAIL** قابل مشاهده در بالای دیالوگ (پیش‌نمایش تصویر انتخاب‌شده)
- **Cut BMP** — ذخیره به پوشه `captures/` و افزودن خودکار به لیست
- **Insert If Else** — غیرفعال‌سازی combo timeout را به دنبال دارد
- **Round-trip**: بازکردن دوباره → مقادیر حفظ می‌شوند
- `MainViewModel.ShowStepDialog` → routing برای `type=="findImage"` به `SearchPictureDialog`

### باگ فیکس‌ها

| مشکل | فیکس |
|------|------|
| `partial void` تکراری با source generator CommunityToolkit | حذف ۳ handler دستی؛ استفاده از `[NotifyPropertyChangedFor]` + فراخوانی مستقیم `UpdateScopeHighlight()` |
| `nested Ams.UI/` — دو پروژِه یکسان (duplicate compile) | حذف دایرکتوری تودرتو: `rm -rf Ams.UI/Ams.UI/` |
| `Brush` مبهم (CS0104) بین Drawing و Media | `System.Windows.Media.Brush` fully qualified در `FlatStepRow.cs` |
| `MessageBox` / `Brushes` مبهم در SearchPictureDialog | `System.Windows.MessageBox` + `System.Windows.Media.Brushes` |

### سخت‌گیری‌های فعال (از v0.7.6-hardened)
تمام ۹ اقدام حفاظتی `VisionService` و ۲ اقدام `openFile`/`RunEngine` روی نسخه v0.7.7 پایه اعمال شدند.

---

## دارک تم — SearchPictureDialog.xaml

وین‌زیپ v0.7.7 رنگ‌های روشن هاردکد داشت (`#FAFBFC`, `White`, `#C9D1D9`).
XAML با توکن‌های `Resources/Tokens.xaml` بازنویسی شد:

| المان | قبل | بعد |
|-------|-----|-----|
| پس‌زمینه پنجره | `#FAFBFC` (سفید) | `BgPanelBrush` (#26272E) |
| TextBox/ComboBox/List | بدون پس‌زمینه | `BgBaseBrush` (#1E1F24) |
| دکمه‌ها | رنگ پیش‌فرض ویندوز | `BgElevatedBrush` (#2E3038) |
| متن اصلی | `#1F2328` (سیاه) | `TextPrimaryBrush` (#E8EAED) |
| متن ثانویه | `#57606A` | `TextSecondaryBrush` (#9AA0A6) |
| حاشیه‌ها | `#C9D1D9` | `BorderSubtleBrush` (#33353D) |
| دکمه OK | رنگ سیستم | `AccentBrush` (#4F8CFF) + سفید |

✅ Build: 0 errors, 0 warnings  
✅ Tests: 25/25 pass

---

## v0.7.8 — Random Package + Hold Range + DelayMax

### ویژگی‌های جدید

#### Random Package (گام ۱۷ام)
- دکمه 🎲 در rail آیکون‌ها
- منوی Insert → Random Package
- **کانتینر + scope** (رنگ صورتی + نوار bracket `PackageBand`)
- فیلدهای dialog:
  - `mode`: `shuffleAll` (همه children یک بار مرتب) / `randomSubset` (تعداد تصادفی)
  - `minCount`: حداقل تعداد children
  - `maxCount`: حداکثر تعداد children

#### Delay Max (ms) — فیلد جدید در تمام دیالوگ‌ها
- وقتی `DelayMax > Delay` باشد → تاخیر بعد از گام به صورت random در `[Delay, DelayMax]`
- وقتی `DelayMax == 0` باشد → از فایل `.amsj` حذف می‌شود (backward compatible)
- `Batch Edit Delays` → ranges را هم اعمال می‌کند
- ستون delay در لیست: `1000–2000 ms` نمایش می‌دهد

#### Hold min/max (ms) — در Mouse Click و Keystroke
- دستورات: `MCLICK|left,1,30,90` / `KCOMBO|162+115,40,120`
- نرمال‌سازی: اگر `holdMin > holdMax` باشد، swap می‌شود
- وقتی هر دو 0 → فرمان firmware 1.6 بدون hold suffix

#### RunEngine
- Fisher–Yates shuffle هر pass (فقط enabled children)
- disabled children از pool حذف می‌شوند
- `PickPackageSteps(StepNode s, Random rng)` — متد pure برای تست
- log: `🎲 random package: ...`

#### ScriptGenerator
- TODO comment برای Random Package
- Delay range: `Step-Delay (Get-Random -Minimum X -Maximum Y)   # random delay range (v0.7.8)`

### تست‌ها
✅ 44/44 پاس (۱۳ تست جدید v0.7.8)

| تست | توضیح |
|------|-------|
| randomPackage definition exists | container/scope/fields |
| hold command strings | `MCLICK\|right,2,30,90` |
| hold min/max swap normalized | 90/30 → 30/90 |
| keystroke with hold range | `KCOMBO|162+115,40,120` |
| DelayMax JSON round-trip | serialize/deserialize preserves |
| DelayMax=0 omitted | clean .amsj files |
| shuffleAll picks enabled | disabled excluded, no duplicates |
| fresh order per pass | 5 iterations checked |
| randomSubset [3,5] bounds | 200 passes |
| min/max swap + pool cap | edge case handled |
| FakeBridge e2e | SETRES + PING commands correct |
| script TODO marker | Random Package in .ps1 |

### باگ فیکس‌ها (کمینه — v0.7.8 zip)

| فایل | مشکل | فیکس |
|------|------|------|
| `FlatStepRow.cs:16,24,43,61` | `Brush` ambiguous (CS0104) | `using Brush = System.Windows.Media.Brush;` alias |
| `SearchPictureDialog.xaml.cs:150,159,166` | `MessageBox` ambiguous | `System.Windows.MessageBox.` |
| `SearchPictureDialog.xaml.cs:186` | `Brushes.Transparent` ambiguous | `System.Windows.Media.Brushes.Transparent` |
| `SearchPictureDialog.xaml` | تم روشن هاردکد (بازگشت از v0.7.7) | re-applied dark theme tokens |

---

## نتایج نهایی Build & Test

| نسخه | Errors | Warnings | Tests |
|------|--------|----------|-------|
| Ams.UI | 0 | 0 | ✅ |
| TestRunner | — | 0 | ✅ 53/53 pass |

---

### خلاصه تغییرات به‌صورت نسخه‌ای

| نسخه | تاریخ | ویژگی‌های کلیدی | تست‌ها |
|------|-------|-----------------|--------|
| v0.7.7 | ۲۰۲۶-08-23 | SearchPictureDialog + hardening حفظ‌شده | 25/25 |
| v0.7.8 | ۲۰۲۶-08-23 | Random Package + Hold + DelayMax | 44/44 |
| v0.7.9 | ۲۰۲۶-08-24 | Rail icons رنگی + If/Else + hardening بازنشانی | 48/48 |
| v0.8.0 | ۲۰۲۶-08-24 | Accordion + scope lines نازک + Search Picture fixes | 53/53 |
| v0.8.1 | ۲۰۲۶-08-24 | Region Picker single-click confirm + RefreshPictureUi | 53/53 |

---

## نکات مهم

- **UseWindowsForms=true** → `System.Drawing` implicit import → CS0104 ambiguity برای `Brush`, `Brushes`, `MessageBox`
- الگوی فیکس: `using Brush = System.Windows.Media.Brush;` alias در فایل یا `System.Windows.*` fully qualified
- وین‌زیپ‌های جدید ممکن است تم دارک را reset کنند — همیشه XAML را با توکن‌های `Tokens.xaml` چک کنید
- ۹ اقدام hardening VisionService در v0.7.8 zip وجود نداشت — فقط از v0.7.7 موجود است
- **v0.7.9** — zip شامل تمام patches بود؛ هر سه fix (Brush/MessageBox/Brushes) + dark theme + hardening بازگردانده ✅
- Rail icons در v0.7.9 از توکن‌های `Tokens.xaml` استفاده می‌کنند (به‌جز delay icon که `#B9C1CB` هاردکد دارد)
- **v0.8.0** — ۵ تست accordion جدید؛ بدون باگ فیکس (zip تمام patches را داشت) ✅
- **v0.8.1** — Region Picker confirm fix (single-click when region exists) + RefreshPictureUi extraction؛ UI interaction bugs — تست واحد ندارد، دستی verify ✅

---

*تولید شده توسط Claude Code — ۲۰۲۶-08-24*

---

## v0.7.9 — Find Image: AMK-style dialog wired + real If/Else + bright rail icons + Warden hardening restored

### ویژگی‌های جدید

**۱. Rail icons رنگی**
- ✅ mouse (blue) · keys (purple) · image (cyan) · sound (amber) · loop (orange) · package (pink) · delay (bright gray #B9C1CB) · note (green)
- قبل: همه `#FFFFFF` سیلوئت تیره

**۲. Find Image → Search Picture dialog (واقعی)**
- دیالوگ از v0.7.7 existed اما هرگز wire نشده بود (generic 15-field dialog باز می‌شد)
- v0.7.9: `MainViewModel.ShowStepDialog` → routing برای `type=="findImage"` به `SearchPictureDialog`
- thumbnail preview (white card) + Cut BMP + View BMP Position + Add/Remove Picture + Comment link + Timeout group + Where/When-found/On-timeout combos + Insert If Else + park-cursor + Step Name + Delay + Delay max
- dark theme مثل Play Options panel

**۳. Real If/Else (گام ۱۲ام)**
- با "Insert If Else" checked → OK دو marker row اضافه می‌کند:
  - `"Else branch — runs when the picture is NOT found"`
  - `"End If"`
- انتخاب Else row و Insert step → داخل شاخه Else قرار می‌گیرد
- drag onto Else row هم کار می‌کند
- run time: picture found → Then (children); not found → Else branch (log: `"find image: Else branch (picture not found)"`)
- Imported AMK scripts' `"Else — n step(s)…"` notes هم recognized می‌شوند
- `FindElseBranch(siblings, ifIndex)` — pure method for tests
- `IsElseMarker()` — comment text starts with "Else"

**۴. Warden hardening RESTORED**
VisionService.cs — ۹ اقدام:
1. cadence jitter `Rng.Next(80, 160)`
2. 30% stochastic template skip (`NextDouble() < 0.3`)
3. ±5px region jitter
4. adaptive polling (static screen 3+ frames → `Rng.Next(200, 400)`)
5. ArrayPool<byte> buffers
6. human-like delay caller side (RunEngine)
7. GetGuiResources GDI guard
8. SHA-256 template IDs logged
9. nested try-finally GDI-safe dispose

RunEngine.cs — ۲ اقدام openFile:
- `MD5` hash tag + `Path.GetFileName` (no full path in log)
- `Task.Delay(Rng.Next(200, 800))` before launch
- `Task.Delay(Rng.Next(100, 300))` between MMOVE and MCLICK (2 locations)

### تست‌ها
✅ 48/48 pass (۴ تست جدید v0.7.9)

| تست | توضیح |
|------|-------|
| Else marker found after the If step | `ReferenceEquals` |
| End If without Else → no branch | returns null |
| scan stops at non-comment sibling | left scope |
| imported AMK Else text recognized | `"Else — …"` prefix |

### fixes اعمال‌شده (کمینه)
**بدون نیاز به fix** — v0.7.9 zip حاوی تمام patches بود:
- `FlatStepRow.cs` — `using Brush = System.Windows.Media.Brush;` ✅
- `SearchPictureDialog.xaml.cs` — `System.Windows.MessageBox` + `System.Windows.Media.Brushes` ✅
- `SearchPictureDialog.xaml` — dark theme tokens ✅
- `VisionService.cs` — ۹ اقدام hardening بازگردانده ✅


---

## v0.8.1 — Region Picker double-click confirm fixed + RefreshPictureUi

### دو root cause fix

**۱. RegionPickerWindow double-click confirm**
- مشکل: WPF ClickCount=1 روی double-click وقتی موس بین کلیک‌ها حرکت کرده (~77px) → proximity check با start point درگ اشتباه بود
- تلاش اول: `_savedW/_savedH` save/restore — شکست خورد (همان reset region)
- تلاش دوم: proximity-based detection با `_lastClickPos` — شکست خورد (فاصله از start point زیاد بود)
- ✅ فیکس نهایی (approach 3): وقتی region معتبر وجود دارد، هر کلیک چپ = confirm. بدون نیاز به زمان/موقعیت. فقط یک کلیک کافی است
- Enter key هم به‌عنوان confirm اضافه شد

**۲. SearchPictureDialog.RefreshPictureUi()**
- مشکل: وقتی اول picture روی placeholder index (0) می‌نشیند، `SelectionChanged` شلیک نمی‌شود → preview خالی، Remove disabled
- فیکس: استخراج `RefreshPictureUi()` و فراخوانی صریح بعد از Add/Cut/Remove

### تست‌ها
✅ 53/53 pass (بدون تست جدید — UI interaction bugs)

### fixes اعمال‌شده (کمینه)
**بدون نیاز به fix** — v0.8.1 zip حاوی تمام patches بود:
- `RegionPickerWindow.xaml.cs` — double-click confirm fix ✅
- `SearchPictureDialog.xaml.cs` — RefreshPictureUi extraction ✅

