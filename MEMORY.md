# Memory Index

- [v0.7.8 random package](v0.7.8-random-package.md) — Random Package (step 17) + hold min/max + DelayMax; Fisher-Yates shuffle; 44/44 tests pass
- [v0.7.7 search picture dialog](v0.7.7-search-picture-dialog.md) — SearchPictureDialog + dark theme tokens + partial void fix + 9 hardening actions preserved; v0.7.8 replaced tree wholesale; CS0104 fixes: Brush alias + MessageBox/Brushes qualified
- [Pipe deadlock in AmkImporter](pipe-deadlock-amk-importer.md) — C# + Python stdout pipe fills → deadlock; fix: read both streams concurrently with UTF-8
- [aborted event bug in PythonBoardBridge](aborted-event-pythonboardbridge.md) — missing case for bridge.py 'aborted' event caused SendAsync to hang; Run button stuck grey
- [v0.7 flat ListBox migration](v0.7-flat-listbox.md) — TreeView→ListBox with Extended multi-select; FlatStepRow proxy; multi-selection on destructive commands; clipboard JSON array
- [v0.7.2 scope structure](v0.7.2-scope-structure.md) — flat ListBox rows tinted by For/If scope; AMK red head/tail lines; UseWindowsForms shadowing System.Drawing.Brush
- [v0.7.3 full src replacement](v0.7.3-full-replace.md) — full src overwrite from zip (no selective merge); StepNode.Children setter critical for File→Open; FlatStepRow partial+Brush fixes
- [v0.7.4 band brackets + rail redesign](v0.7.4-band-brackets.md) — BandSeg (IsFirst/IsLast caps), spaced guide bands, red scope brackets, 7-button icon rail with RailButton style
- [v0.7.5 Play Options panel](v0.7.5-play-options.md) — repeat once/N-times/timed + shutdown + save log; IsScopeCap fix for bracket corners
- [Image Search System](image-search-system.md) — NCC + integral image, GDI screen capture, 120ms poll, scope modes

---

## v0.9.21 — opهای فوری صفحه‌کلید در حالت موازی (2026-09-01)

**گزارش:** اجرای موازی در v0.9.20 نه‌تنها برطرف نشد، بدتر به نظر رسید.

**اثبات از رکورد اجرای واقعی** (ضبط با رکوردر AMS قدیمی — خط اول `Key Up : F1`):
- cadence کلید میانه‌ی **۴۰۸ms** در برابر کانفیگ ~۱۹۰ms → تاخیر دوبله: برد ~۱۹۰ms + اپ ~۱۹۰ms. تایپ نیم‌سرعت = «بدتر شده».
- فریزهای موس **۸٫۶s** (۳۴ کلید در خلال) و **۶٫۷s** (۲۸ کلید) حین تایپ.
- تله‌پورت = **۰** → لنگر `_mouseAnchor` کار کرد.

**ریشه:** firmware حتی به KTEXT تک‌کاراکتری تاخیر per-key سمت‌برد اعمال می‌کند و bridge تا پاسخ نهایی صبر می‌کند → هر op صدها ms کانال تک‌سریال را نگه می‌داشت + مکث سمت‌اپ من دوبله شد.

**رفع:** در حالت موازی هر کاراکتر = `KTEXT|0,0,<c>` (op فوری ~۱۰ms) و **تمام** پیسی‌گذاری انسانی سمت اپ (`NextRandom(hmin,hmax)`). همان مدل اپ AMS قدیمی (رکوردش: Key Down/Up + Delay).
**پلن B مستندشده:** `KDOWN|vk`/`KUP|vk` به‌ازای هر کاراکتر — هر دو «verified against firmware 1.6» در README و در strings فلش برد.

**نکته‌ی فرایندی:** `test-output.txt` در بیلد 34 هنوز ۲۴ اوت بود — گام‌های ۱۹-۲۱ هرگز توسط Claude Code اجرا نشده‌اند. اجرای TestRunner در CLAUDE-IMPLEMENT اجباری + بایگانی خروجی تازه.

**فایل‌ها:** RunEngine.cs (ChunkKtextForParallel → هدر 0,0)، TestRunner گام ۲۱ به‌روز، بنر v0.9.21، csproj 0.9.21، docs/parallel-interleave-v0.9.21.md، CLAUDE-IMPLEMENT-v0.9.21.md.

---

## v0.9.23 — پیش‌فرض‌های انسانی + کالیبراسیون + مهار موس هنگام تایپ (2026-09-01)

(v0.9.22 فقط پرامپت بود و build نشد؛ محتوایش در این نسخه ادغام شد.)

**مبنای آماری** (رکورد واقعی کاربر، ۵۷٫۸s): سرعت موس median ≈ 140 px/s · p99 ≈ 452 · cadence تایپ median ≈ 204ms · مکث موس حین تایپ 38 بار ≥100ms در 58s.

**۱) پیش‌فرض‌های کالیبره‌شده:**
- سرعت موس Options: 0/2300 → **150/500** (`AppSettings` + `HumanMouse.Config` + fallback shapeOnly)
- typeText: hmin/hmax 25/70 → **80/220**
- randomMousePosition: idlePause 1000/5000 → **800/3000**
- مهاجرت `NormalizeSpeedDefaults`: فقط 0/2300 کارخانه → 150/500؛ سفارشی و 0/0 حفظ می‌شوند.
- Options: توضیح شفاف + دکمه‌ی «Reset to human defaults».

**۲) «Learn from my hand»:** `CalibrationAnalyzer` (خالص، p25/p85 + clamp، حداقل نمونه) + `CalibrationWindow` (ضبط ۲۰s داخل WPF — فقط زمان‌بندی/سرعت، هویت کلید هرگز ثبت نمی‌شود). نتیجه → Options boxes + `AppSettings.TypeKeyMinMs/MaxMs` → `StepDefinitions.TypingFallback*` (زنده).

**۳) مهار موس هنگام تایپ:** تحلیل رکورد v0.9.21 نشان داد p90 تأخیر موس-بعد-از-کلید 43ms بود در برابر 982ms انسانی → موس بیش‌ازحد فعال. رفع: سیگنال `Interlocked` از شاخه‌ی صفحه‌کلید؛ شاخه‌ی موس وقتی تایپ فعال است (پنجره‌ی ۹۰۰ms) نیم‌سرعت می‌شود و بعد از هر ۲–۶ ضربه مکث نامنظم ۱۲۰–۵۰۰ms (۱۰٪: ۵۰۰–۱۲۰۰ms) می‌گیرد. همه app-side و pause-aware؛ صف‌شدن فرمان نداریم.

**۴) هاتکی:** `border.Focus()` → `Focusable=true; Keyboard.Focus(border); e.Handled=true` — اصلاح v0.9.21 قابل‌اتکا نبود (Border پیش‌فرض focusable نیست).

**تست:** گام ۲۲ (۷ assertion پیش‌فرض/مهاجرت) + گام ۲۳ (۸ assertion مهار/کالیبراسیون).

**فایل‌ها:** DocumentService، HumanMouse، RunEngine، CalibrationAnalyzer(جدید)، CalibrationWindow(جدید)، OptionsDialog.xaml(.cs)، StepDefinitions، MainViewModel، csproj 0.9.23، TestRunner، docs/human-defaults-calibration-v0.9.23.md، CLAUDE-IMPLEMENT-v0.9.23.md.

---

## v0.9.24 — دیالوگ‌های فارسی + کالیبراسیون مجدد سرعت (2026-09-01)

**۱) wiggle رد شد (تصمیم مستند):** presence wiggle برای زنده‌ماندن نشانگر هنگام تایپ، به‌خاطر نگرانی آنتی‌چیت بازی‌های آنلاین **رد شد**. راه‌حل پذیرفته‌شده: خاموش‌کردن «Hide pointer while typing» در ویندوز. هیچ حرکت مصنوعی اضافی در اپ نیست.

**۲) کالیبراسیون مجدد سرعت:** رکورد متراکم جدید دست کاربر (۶۲۶۹ نمونه، ~۱ms) نشان داد پیش‌فرض v0.9.23 (150/500 px/s، از رکورد کم‌تراکم ~۱۸ms) دو تا شش برابر کندتر از دست واقعی است. با هموارسازی ۴۰ms (ضد tremor): p25 ≈ 416 · median ≈ 980 · p75 ≈ 1970 px/s. پیش‌فرض‌های جدید: **300/2000** (AppSettings + OptionsDialog + HumanMouse.Config + fallback shapeOnly + دکمه‌ی Reset). مهاجرت فقط 0/2300 کارخانه → (300,2000)؛ تنظیمات موجود حفظ می‌شود. randomMousePosition: overshootChance 15→**25** (دست کاربر ۲/۴ overshoot داشت) و midPauseMax 400→**500** (hesitationهای ۲۹۷–۴۸۵ms). سه assertion گام ۲۲ عمداً به‌روز و مستند شدند.

**۳) دیالوگ‌های فارسی:** فایل جدید `Models/StepTextsFa.cs` — دیکشنری `stepType:fieldKey` ← `fieldKey` ← fallback انگلیسی. اتصال در StepDialog: برچسب‌ها فارسی + راست‌چین، CheckBoxها فارسی، عنوان «جدید:/ویرایش:»، دکمه‌ها «تأیید/انصراف». **گزینه‌ها و مقادیر انگلیسی می‌مانند** (درخواست کاربر). `StepDefinitions.FindTypeByFields` (جدید) نوع استپ را از مرجع Fields حل می‌کند — call siteها تغییر نکردند. دیالوگ‌های خاص (SearchPictureDialog/RegionPicker/Options) و خلاصه‌ی درخت عمداً خارج از scope مانده‌اند.

**تست:** گام ۲۴ (۷ assertion فارسی/برخورد/fallback/FindTypeByFields/پیش‌فرض‌ها).

**فایل‌ها:** StepTextsFa.cs(جدید)، StepDefinitions، StepDialog.xaml(.cs)، DocumentService، HumanMouse، OptionsDialog.xaml(.cs)، MainViewModel (بنر v0.9.24)، csproj 0.9.24، TestRunner، docs/persian-ui-and-speed-v0.9.24.md، CLAUDE-IMPLEMENT-v0.9.24.md.

**درس فرایندی (splice10):** لنگر از روی خروجی sed-نرمال‌شده‌ی grep ساخته بودم و شکست خورد (`FieldKind.` حذف شده بود) — قاعده: لنگر همیشه از محتوای خام فایل، نه خروجی پایپ‌شده. assert-before-write درخت را سالم نگه داشت.

---

## v0.9.25 — پوشش کامل فارسی (2026-09-01)

**گزارش:** v0.9.24 «بطور کامل فارسی نشده — همه توضیحات فیلدها در همه بخش‌ها». تشخیص درست بود: لایه فقط StepDialog عمومی را پوشش می‌داد.

**پوشش جدید:** SearchPictureDialog (Find Image — همه‌ی هدر/برچسب/دکمه/Combo/تولتیپ + ۳ MessageBox) · OptionsDialog (تب‌ها + برچسب‌ها + هاتکی‌ها) · RegionPicker · CalibrationWindow (متن + پیام‌های interpolated کد) · MainWindow (Play Options + Inspector + لاگ سریال + ۱۰ تولتیپ ریل + مکث/ادامه) · StepDialog.xaml.cs (Calibrate/Browse/Pick region + اعتبارسنجی با نام فارسی فیلد) · MainViewModel (عنوان batch + ۴ خطای فایل).

**قانون حفظ‌شده:** گزینه‌ها/مقادیر/واحدها/نام اکشن‌ها/منوها انگلیسی می‌مانند.
**پایداری پلن‌ها:** Comboهای Find Image با SelectedIndex نگاشت می‌شوند → ترجمه‌ی متن نمایشی پلن‌های ذخیره‌شده را نمی‌شکند (ترتیب ثابت).

**کد فراتر از متن:** `StepDefinitions.All` (enumerate) + `StepTextsFa.Has` (پوشش bool) — برای sweep گام ۲۵ که همه‌ی تعریف‌ها × فیلدها را می‌پیماید و جاماندن کلید را برای همیشه می‌گیرد.

**تست:** گام ۲۵ — ۷ assertion (sweep کامل + نگهبان فایلی XAMLها با walk-up path resolution).

**درس فرایندی:** ۱) کامنت HTML داخل تگ XML = MC3000 (v0.9.24، اصلاح Claude) — در ویرایش XAML کامنت اضافه نکن. ۲) لنگر پایتونی با `\n` داخل رشته‌ی C# باید `\\n` باشد (splice11b) — assert-before-write درخت را سالم نگه داشت.

**فایل‌ها:** ۹ فایل UI + MainViewModel + StepDefinitions + StepTextsFa + csproj 0.9.25 + TestRunner + docs/persian-full-coverage-v0.9.25.md + CLAUDE-IMPLEMENT-v0.9.25.md.

---

## v0.9.26 — موس روان حین تایپ: مهار با سقف + استراحت‌های کم‌تعداد (2026-09-02)

**گزارش:** در Parallel Group وقتی تایپ شروع می‌شود موس «تکه‌تکه» و با قطع‌ووصل حرکت می‌کند (رکورد کاربر فرستاده شد).

**شواهد (رکورد ۷۲٫۶s اپ با پلن pj6 + رکورد متراکم ۲۰٫۲s دست):**
- اپ: ۷۷ مکث ≥۱۰۰ms حین تایپ؛ ۱۱ فریز ≥۵۰۰ms؛ دو فریز میان‌مسیر **۱۲٫۴s و ۱۱٫۰s** در حالی که ۸۲ و ۷۶ ضربه‌ی کلید در همان بازه‌ها با کادنس عادی رد شدند → کانال سریال سالم بود؛ شاخه‌ی موس در یک await طولانی پارک شده بود. هر دو فریز با همان پیکسل (±۳px) شروع و تمام شدند = تاخیرهای کشیده روی نقاط زیرپیکسل دمِ مسیر.
- دست: حین تایپ p90 گپ موس ۶ms، حداکثر ۳۵۱ms، صفر فریز ≥۵۰۰ms.

**ریشه:** ۱) `SuppressedMouseDelayMs` بدون سقف (×۲) — با moveTime تا ۷۰۰۰ms در پلن، تاخیرهای دمِ مسیر ثانیه‌ای دوبرابر می‌شدند. ۲) `MaybeTypingRestAsync` هر ۲–۶ ضربه استراحت ۱۲۰–۵۰۰ms (۱۰٪ تا ۱۲۰۰ms) — پنجره‌ی ۹۰۰msی IsTypingActive در burst پیوسته هرگز نمی‌گذرد پس استراحت‌ها پشت‌سرهم می‌افتادند.

**رفع:** سقف ۱۴۰ms برای مهار (`SuppressedMouseDelayCapMs` — حس نیم‌سرعت حفظ، هیچ تاخیر منفردی ثانیه‌ای نمی‌شود) + کادنس استراحت هر ۱۰–۲۴ ضربه با ۹۰–۳۰۰ms (۱۰٪: ۳۵۰–۷۰۰ms) در `NextTypingRestEveryKeys`/`TypingRestMs` (خالص، تست‌پذیر). همه app-side و pause-aware؛ پروتکل برد و send_path دست‌نخورده.

**چرا مسیر ردشده:** حذف کامل مهار (برگشت به v0.9.21) رد شد — همان «موس بیش‌ازحد فعال» بود (p90 تأخیر موس-بعد-از-کلید 43ms در برابر 982ms انسانی). نیم‌سرعتِ با سقف هر دو داده را ارضا می‌کند.

**تست:** گام ۲۶ — ۷ assertion (سقف، کادنس ۱۰–۲۴، طول ۹۰–۷۰۰، نرخ ~۱۰٪). گام ۲۳ دست‌نخورده (assertهایش زیر سقف‌اند).

**درس فرایندی:** مهار رفتاری بدون سقف روی ورودی کنفیگ‌شدنی (moveTime تا ۷۰۰۰ms) = بمب زمانی؛ هر ضریب روی زمان‌بندی کاربر باید clamp داشته باشد. رکورد متراکم دست (p90 گپ ۶ms حین تایپ) معیار قطعی «روان‌بودن» شد — انسان حین تایپ موس را نمی‌پارکد، فقط گاهی بین حرکت‌ها می‌نشیند.

**فایل‌ها:** RunEngine.cs (SuppressedMouseDelayMs + SuppressedMouseDelayCapMs + MaybeTypingRestAsync + NextTypingRestEveryKeys + TypingRestMs)، بنر v0.9.26، csproj 0.9.26، TestRunner گام ۲۶، docs/mouse-typing-glide-v0.9.26.md، CLAUDE-IMPLEMENT-v0.9.26.md.

---

## v0.9.27 — صدای فوری در Parallel Group: MediaPlayer روی Dispatcher (2026-09-02)

**گزارش:** در پلن 2.amsj (تایپ موازی + findImage → playAudio) آهنگ با تاخیر ۵–۱۰ ثانیه پخش شد؛ هیچ Delayای تنظیم نشده بود.

**حذف مسیرهای بی‌گناه (داده/کد):** نگاشت کمبوی timeoutUnit سالم است (`ms→0, second→1, minute→2, hour→3` هر دو جهت) — `timeoutUnit: "ms"` در فایل واقعی است، regression ترجمه‌ی v0.9.25 نیست. با timeout=80ms تصویر باید همان poll اول پیدا شده باشد (وگرنه صدا هرگز نمی‌آمد) → تاخیر در vision نبوده. polling تطبیقی حداکثر ~۴۰۰ms است.

**ریشه:** thread-affinity ـی `MediaPlayer`. مسیر ترتیبی روی UI thread ادامه می‌یابد (await + SynchronizationContext) ولی شاخه‌های Parallel Group با `Task.Run` روی thread-pool بدون Dispatcher pump می‌روند → `Open/Play` ثانیه‌ها گیر می‌کند و `MediaEnded` هرگز fire نمی‌شود (loop شکسته + نشت پلیر غیرلوپ تا پایان run).

**رفع:** همه‌ی کارهای پلیر (ساختن، Open، Play، اتصال MediaEnded) داخل `Application.Current.Dispatcher.Invoke`؛ `StopAllAudio` هم مارشال می‌شود + نگهبان HasShutdownStarted (هنگام خروج اپ Invoke همزمان hang نکند — sweep مستقیم fallback). مسیر ترتیبی بدون تغییر رفتار.

**چرا مسیر ردشده:** جابه‌جایی کل RunEngine روی UI thread رد شد — engine باید background بماند (لاگ/پاسخ‌گویی)؛ فقط مالکیت پلیر به UI سپرده شد. راه‌حل جایگزین آینده در صورت نیاز: نخ STA اختصاصی صدا با Dispatcher.Run.

**تست:** گام ۲۷ — ۵ assertion نگهبان فایلی (الگوی گام ۲۵). گام‌های قبلی دست‌نخورده.

**درس فرایندی:** هر ساخت/لمس WPF object با affinity (MediaPlayer، MediaElement، DispatcherObject) باید روی نخ دارای pump باشد؛ «روی کدام نخ ادامه می‌یابد؟» را هنگام افزودن قابلیت به شاخه‌های موازی بپرس — await روی UI شروع می‌شود ولی Task.Run در runner موازی آن را می‌شکند.

**فایل‌ها:** RunEngine.cs (کیس playAudio + StopAllAudio)، بنر v0.9.27، csproj 0.9.27، TestRunner گام ۲۷، docs/audio-dispatcher-v0.9.27.md، CLAUDE-IMPLEMENT-v0.9.27.md.

---

## v0.9.28 — تشخیص فوری تصویر: گرم‌کردن vision + دور اول همیشه‌جست‌وجو (2026-09-02)

**گزارش:** با پلن 2.amsj جدید صدا ~۱۵ ثانیه بعد از دیده‌شدن تصویر پخش شد، حتی بعد از v0.9.27 («انگار توی صف می‌ره»).

**شواهد:** diff پلن قدیم→جدید: `searchScope: region(338×108) → entireScreen`. تاخیر ران قدیم (۵–۱۰s) صدا-سمت بود (MediaPlayer بدون pump — رفع v0.9.27)؛ تاخیر ران جدید vision-سمت است. تایپ آزادانه جریان داشت → صفی در کار نبود.

**ریشه:** در entireScreen هر دور جست‌وجو = ۴ نوار تمام‌صفحه × (کپچر GDI + دو انتگرال‌ایمیج + NCC هرمی + refine ≤۸ کاندید) و دور **اول** هزینه‌ی سرد دارد: tier-0 JIT کل مسیر داغ + تخصیص LOH + اولین کپچر — جمعاً ~۱۵s. تایم‌اوت (effectiveTimeout = timeoutMs/0.7) فقط **بین** دورها چک می‌شد و skip تصادفی ۳۰٪ (action 2) می‌توانست قالب را از دور اول حذف کند.

**رفع:** ۱) `VisionService.Warmup()` — self-match مصنوعی ۹۶×۶۴/۳۶×۳۶ با Random(28) که کل مسیر داغ را در ابتدای RunAsync گرم می‌کند ۲) skip فقط بعد از دور اول (`polls > 0 &&`) ۳) چک ct + تایم‌اوت بین نوارها (Stop/timeout وسط دور سنگین گیر نمی‌کند) ۴) لاگ `poll round N took X ms` برای شواهد ران بعدی.

**چرا مسیر ردشده:** بازنویسی عمیق matcher برای reuse فریم/انتگرال بین قالب‌ها و نوارها رد شد — بدون اجرای ویندوزی قابل‌اعتماد نیست و ریسک رگرسیون روی پرتست‌ترین زیرسیستم (گام‌های ۱۹–۲۰) بالاست؛ اول شواهد زمان‌بندی هر دور با لاگ جدید، بعد بهینه‌سازی هدفمند.

**تست:** گام ۲۸ — ۵ assertion (Warmup اجرایی واقعی + ۴ نگهبان فایلی). گام‌های قبلی دست‌نخورده. اصلاح MediaEnded-scope ـی Claude Code در TestRunner مرج شد.

**درس فرایندی:** هزینه‌ی سرد (cold JIT/alloc) را در تحلیل تاخیر جدی بگیر — الگوریتم گرم sub-second بود، سرد ۱۵s. و: diff فایل پلن بین دو ران، ارزان‌ترین ابزار تشخیص است؛ اول آن را بخوان.

**فایل‌ها:** VisionService.cs (Warmup + شرط skip + چک‌های نوار + لاگ دور)، RunEngine.cs (فراخوانی Warmup در RunAsync)، بنر v0.9.28، csproj 0.9.28، TestRunner گام ۲۸، docs/vision-warmup-v0.9.28.md، CLAUDE-IMPLEMENT-v0.9.28.md.

---

## v0.9.29 — دیالوگ لوپ شفاف + زنده‌شدن برچسب‌های فارسی per-step (2026-09-02)

**گزارش:** اسکرین‌شات دیالوگ For Loop — فیلدهای count و time در هر سه حالت فعال؛ «اگه ۱۰ دقیقه بدون محدودیت، پس چرا دو فیلد؟ تناقضه».

**پاسخ مفهومی:** تناقض رفتاری نیست — `mode` قانون را انتخاب می‌کند (count = تعداد بار / time = timeValue×timeUnit / infinite = تا Stop با Shift+F2) و فیلدهای دیگر خنثی‌اند؛ مشکل نمایش همیشگی همه بود.

**باگ ۱ — نمایش شرطی لوپ:** ماشینری v0.9.14 فقط «پنهان وقتی مساوی» (HideWhenValue) داشت؛ لوپ سه قانون دارد و count باید در دو حالت پنهان شود. رفع: `HideUnlessValue` در FieldDef (پارامتر اختیاری انتهایی رکورد — call siteهای قدیمی نشکستند) + فایل جدید `Models/StepFieldVisibility.cs` با `FieldVisible(depValue, hideWhen, hideUnless)` خالص و تست‌پذیر + اعمال در ApplyConditionalVisibility. قواعد: count → HideUnlessValue="count"، timeValue/timeUnit → "time"؛ infinite همه را پنهان می‌کند.

**باگ ۲ — برچسب‌های per-step مرده (از v0.9.24!):** `_stepType = FindTypeByFields(fields)` روی آرایه‌ی **الحاق‌شده** (فیلدهای استپ + __name/__delay/__delayMax) صدا زده می‌شد و reference-match هیچ‌وقت اتفاق نمی‌افتاد → `_stepType` همیشه null → کل `FaByStep` (mode/text/path/x/y/w/h/label…) بی‌صدا fallback انگلیسی می‌گرفت. sweep گام ۲۵ دیکشنری را مستقیم تست می‌کرد نه مسیر دیالوگ را — برای همین جاماند. رفع: پارامتر صریح `stepType` در ctor دیالوگ از MainViewModel (`type` در scope بود) + fallback قدیمی برای دیالوگ ویرایش گروهی.

**فارسی‌سازی پوسته:** `__name`/`__delay`/`__delayMax` به دیکشنری عمومی Fa اضافه شد («نام استپ» / «تأخیر بعد از استپ (ms)» / توضیح فارسی delayMax) — فیلدهای مشترک همه‌ی دیالوگ‌ها که انگلیسی مانده بودند.

**تست:** گام ۲۹ — ۶ assertion (FieldVisible سه‌حالته + رفتار v0.9.14 ثابت + برچسب‌های پوسته + حل‌شدن forLoop:mode به فارسی + نگهبان پاس صریح stepType).

**درس فرایندی:** ۱) sweep روی داده، بدون تست مسیر مصرف‌کننده‌ی واقعی، حفره‌ی پوشش می‌سازد — نگهبان فایلی برای call site بگذار. ۲) resolution بر پایه‌ی reference equality روی آرایه‌های مشتق‌شده بمب خاموش است؛ شناسه‌ی صریح بفرست.

**فایل‌ها:** StepDefinitions (HideUnlessValue + قواعد لوپ)، StepFieldVisibility.cs (جدید)，StepDialog (stepType صریح + قاعده‌ی جدید)، StepTextsFa (۳ کلید پوسته)، MainViewModel (پاس type + بنر)، csproj 0.9.29، TestRunner گام ۲۹، docs/loop-dialog-clarity-v0.9.29.md，CLAUDE-IMPLEMENT-v0.9.29.md.

**ریلیز:** `Classroom-Studio-v0.9.29-release.zip` (۲۴۳۶ KB، ۸ فایل: exe+dll+deps+bridge.py) در Downloads ✅
**تست‌ها:** ۳۲۶/۳۲۶ پاس — گام ۲۹: ۶ assertion (FieldVisible سه‌حالته + v0.9.14 unchanged + پوسته فارسی + stepType صریح)

**ریلیز:** `Classroom-Studio-v0.9.30-release.zip` (۲۴۳۸ KB، ۸ فایل: exe+dll+deps+bridge.py) در Downloads ✅# Memory Index

- [v0.7.8 random package](v0.7.8-random-package.md) — Random Package (step 17) + hold min/max + DelayMax; Fisher-Yates shuffle; 44/44 tests pass
- [v0.7.7 search picture dialog](v0.7.7-search-picture-dialog.md) — SearchPictureDialog + dark theme tokens + partial void fix + 9 hardening actions preserved; v0.7.8 replaced tree wholesale; CS0104 fixes: Brush alias + MessageBox/Brushes qualified
- [Pipe deadlock in AmkImporter](pipe-deadlock-amk-importer.md) — C# + Python stdout pipe fills → deadlock; fix: read both streams concurrently with UTF-8
- [aborted event bug in PythonBoardBridge](aborted-event-pythonboardbridge.md) — missing case for bridge.py 'aborted' event caused SendAsync to hang; Run button stuck grey
- [v0.7 flat ListBox migration](v0.7-flat-listbox.md) — TreeView→ListBox with Extended multi-select; FlatStepRow proxy; multi-selection on destructive commands; clipboard JSON array
- [v0.7.2 scope structure](v0.7.2-scope-structure.md) — flat ListBox rows tinted by For/If scope; AMK red head/tail lines; UseWindowsForms shadowing System.Drawing.Brush
- [v0.7.3 full src replacement](v0.7.3-full-replace.md) — full src overwrite from zip (no selective merge); StepNode.Children setter critical for File→Open; FlatStepRow partial+Brush fixes
- [v0.7.4 band brackets + rail redesign](v0.7.4-band-brackets.md) — BandSeg (IsFirst/IsLast caps), spaced guide bands, red scope brackets, 7-button icon rail with RailButton style
- [v0.7.5 Play Options panel](v0.7.5-play-options.md) — repeat once/N-times/timed + shutdown + save log; IsScopeCap fix for bracket corners
- [Image Search System](image-search-system.md) — NCC + integral image, GDI screen capture, 120ms poll, scope modes

---

## v0.9.21 — opهای فوری صفحه‌کلید در حالت موازی (2026-09-01)

**گزارش:** اجرای موازی در v0.9.20 نه‌تنها برطرف نشد، بدتر به نظر رسید.

**اثبات از رکورد اجرای واقعی** (ضبط با رکوردر AMS قدیمی — خط اول `Key Up : F1`):
- cadence کلید میانه‌ی **۴۰۸ms** در برابر کانفیگ ~۱۹۰ms → تاخیر دوبله: برد ~۱۹۰ms + اپ ~۱۹۰ms. تایپ نیم‌سرعت = «بدتر شده».
- فریزهای موس **۸٫۶s** (۳۴ کلید در خلال) و **۶٫۷s** (۲۸ کلید) حین تایپ.
- تله‌پورت = **۰** → لنگر `_mouseAnchor` کار کرد.

**ریشه:** firmware حتی به KTEXT تک‌کاراکتری تاخیر per-key سمت‌برد اعمال می‌کند و bridge تا پاسخ نهایی صبر می‌کند → هر op صدها ms کانال تک‌سریال را نگه می‌داشت + مکث سمت‌اپ من دوبله شد.

**رفع:** در حالت موازی هر کاراکتر = `KTEXT|0,0,<c>` (op فوری ~۱۰ms) و **تمام** پیسی‌گذاری انسانی سمت اپ (`NextRandom(hmin,hmax)`). همان مدل اپ AMS قدیمی (رکوردش: Key Down/Up + Delay).
**پلن B مستندشده:** `KDOWN|vk`/`KUP|vk` به‌ازای هر کاراکتر — هر دو «verified against firmware 1.6» در README و در strings فلش برد.

**نکته‌ی فرایندی:** `test-output.txt` در بیلد 34 هنوز ۲۴ اوت بود — گام‌های ۱۹-۲۱ هرگز توسط Claude Code اجرا نشده‌اند. اجرای TestRunner در CLAUDE-IMPLEMENT اجباری + بایگانی خروجی تازه.

**فایل‌ها:** RunEngine.cs (ChunkKtextForParallel → هدر 0,0)، TestRunner گام ۲۱ به‌روز، بنر v0.9.21، csproj 0.9.21، docs/parallel-interleave-v0.9.21.md، CLAUDE-IMPLEMENT-v0.9.21.md.

---

## v0.9.23 — پیش‌فرض‌های انسانی + کالیبراسیون + مهار موس هنگام تایپ (2026-09-01)

(v0.9.22 فقط پرامپت بود و build نشد؛ محتوایش در این نسخه ادغام شد.)

**مبنای آماری** (رکورد واقعی کاربر، ۵۷٫۸s): سرعت موس median ≈ 140 px/s · p99 ≈ 452 · cadence تایپ median ≈ 204ms · مکث موس حین تایپ 38 بار ≥100ms در 58s.

**۱) پیش‌فرض‌های کالیبره‌شده:**
- سرعت موس Options: 0/2300 → **150/500** (`AppSettings` + `HumanMouse.Config` + fallback shapeOnly)
- typeText: hmin/hmax 25/70 → **80/220**
- randomMousePosition: idlePause 1000/5000 → **800/3000**
- مهاجرت `NormalizeSpeedDefaults`: فقط 0/2300 کارخانه → 150/500؛ سفارشی و 0/0 حفظ می‌شوند.
- Options: توضیح شفاف + دکمه‌ی «Reset to human defaults».

**۲) «Learn from my hand»:** `CalibrationAnalyzer` (خالص، p25/p85 + clamp، حداقل نمونه) + `CalibrationWindow` (ضبط ۲۰s داخل WPF — فقط زمان‌بندی/سرعت، هویت کلید هرگز ثبت نمی‌شود). نتیجه → Options boxes + `AppSettings.TypeKeyMinMs/MaxMs` → `StepDefinitions.TypingFallback*` (زنده).

**۳) مهار موس هنگام تایپ:** تحلیل رکورد v0.9.21 نشان داد p90 تأخیر موس-بعد-از-کلید 43ms بود در برابر 982ms انسانی → موس بیش‌ازحد فعال. رفع: سیگنال `Interlocked` از شاخه‌ی صفحه‌کلید؛ شاخه‌ی موس وقتی تایپ فعال است (پنجره‌ی ۹۰۰ms) نیم‌سرعت می‌شود و بعد از هر ۲–۶ ضربه مکث نامنظم ۱۲۰–۵۰۰ms (۱۰٪: ۵۰۰–۱۲۰۰ms) می‌گیرد. همه app-side و pause-aware؛ صف‌شدن فرمان نداریم.

**۴) هاتکی:** `border.Focus()` → `Focusable=true; Keyboard.Focus(border); e.Handled=true` — اصلاح v0.9.21 قابل‌اتکا نبود (Border پیش‌فرض focusable نیست).

**تست:** گام ۲۲ (۷ assertion پیش‌فرض/مهاجرت) + گام ۲۳ (۸ assertion مهار/کالیبراسیون).

**فایل‌ها:** DocumentService، HumanMouse، RunEngine، CalibrationAnalyzer(جدید)، CalibrationWindow(جدید)، OptionsDialog.xaml(.cs)، StepDefinitions، MainViewModel، csproj 0.9.23، TestRunner، docs/human-defaults-calibration-v0.9.23.md، CLAUDE-IMPLEMENT-v0.9.23.md.

---

## v0.9.24 — دیالوگ‌های فارسی + کالیبراسیون مجدد سرعت (2026-09-01)

**۱) wiggle رد شد (تصمیم مستند):** presence wiggle برای زنده‌ماندن نشانگر هنگام تایپ، به‌خاطر نگرانی آنتی‌چیت بازی‌های آنلاین **رد شد**. راه‌حل پذیرفته‌شده: خاموش‌کردن «Hide pointer while typing» در ویندوز. هیچ حرکت مصنوعی اضافی در اپ نیست.

**۲) کالیبراسیون مجدد سرعت:** رکورد متراکم جدید دست کاربر (۶۲۶۹ نمونه، ~۱ms) نشان داد پیش‌فرض v0.9.23 (150/500 px/s، از رکورد کم‌تراکم ~۱۸ms) دو تا شش برابر کندتر از دست واقعی است. با هموارسازی ۴۰ms (ضد tremor): p25 ≈ 416 · median ≈ 980 · p75 ≈ 1970 px/s. پیش‌فرض‌های جدید: **300/2000** (AppSettings + OptionsDialog + HumanMouse.Config + fallback shapeOnly + دکمه‌ی Reset). مهاجرت فقط 0/2300 کارخانه → (300,2000)؛ تنظیمات موجود حفظ می‌شود. randomMousePosition: overshootChance 15→**25** (دست کاربر ۲/۴ overshoot داشت) و midPauseMax 400→**500** (hesitationهای ۲۹۷–۴۸۵ms). سه assertion گام ۲۲ عمداً به‌روز و مستند شدند.

**۳) دیالوگ‌های فارسی:** فایل جدید `Models/StepTextsFa.cs` — دیکشنری `stepType:fieldKey` ← `fieldKey` ← fallback انگلیسی. اتصال در StepDialog: برچسب‌ها فارسی + راست‌چین، CheckBoxها فارسی، عنوان «جدید:/ویرایش:»، دکمه‌ها «تأیید/انصراف». **گزینه‌ها و مقادیر انگلیسی می‌مانند** (درخواست کاربر). `StepDefinitions.FindTypeByFields` (جدید) نوع استپ را از مرجع Fields حل می‌کند — call siteها تغییر نکردند. دیالوگ‌های خاص (SearchPictureDialog/RegionPicker/Options) و خلاصه‌ی درخت عمداً خارج از scope مانده‌اند.

**تست:** گام ۲۴ (۷ assertion فارسی/برخورد/fallback/FindTypeByFields/پیش‌فرض‌ها).

**فایل‌ها:** StepTextsFa.cs(جدید)، StepDefinitions، StepDialog.xaml(.cs)، DocumentService، HumanMouse، OptionsDialog.xaml(.cs)، MainViewModel (بنر v0.9.24)، csproj 0.9.24، TestRunner، docs/persian-ui-and-speed-v0.9.24.md، CLAUDE-IMPLEMENT-v0.9.24.md.

**درس فرایندی (splice10):** لنگر از روی خروجی sed-نرمال‌شده‌ی grep ساخته بودم و شکست خورد (`FieldKind.` حذف شده بود) — قاعده: لنگر همیشه از محتوای خام فایل، نه خروجی پایپ‌شده. assert-before-write درخت را سالم نگه داشت.

---

## v0.9.25 — پوشش کامل فارسی (2026-09-01)

**گزارش:** v0.9.24 «بطور کامل فارسی نشده — همه توضیحات فیلدها در همه بخش‌ها». تشخیص درست بود: لایه فقط StepDialog عمومی را پوشش می‌داد.

**پوشش جدید:** SearchPictureDialog (Find Image — همه‌ی هدر/برچسب/دکمه/Combo/تولتیپ + ۳ MessageBox) · OptionsDialog (تب‌ها + برچسب‌ها + هاتکی‌ها) · RegionPicker · CalibrationWindow (متن + پیام‌های interpolated کد) · MainWindow (Play Options + Inspector + لاگ سریال + ۱۰ تولتیپ ریل + مکث/ادامه) · StepDialog.xaml.cs (Calibrate/Browse/Pick region + اعتبارسنجی با نام فارسی فیلد) · MainViewModel (عنوان batch + ۴ خطای فایل).

**قانون حفظ‌شده:** گزینه‌ها/مقادیر/واحدها/نام اکشن‌ها/منوها انگلیسی می‌مانند.
**پایداری پلن‌ها:** Comboهای Find Image با SelectedIndex نگاشت می‌شوند → ترجمه‌ی متن نمایشی پلن‌های ذخیره‌شده را نمی‌شکند (ترتیب ثابت).

**کد فراتر از متن:** `StepDefinitions.All` (enumerate) + `StepTextsFa.Has` (پوشش bool) — برای sweep گام ۲۵ که همه‌ی تعریف‌ها × فیلدها را می‌پیماید و جاماندن کلید را برای همیشه می‌گیرد.

**تست:** گام ۲۵ — ۷ assertion (sweep کامل + نگهبان فایلی XAMLها با walk-up path resolution).

**درس فرایندی:** ۱) کامنت HTML داخل تگ XML = MC3000 (v0.9.24، اصلاح Claude) — در ویرایش XAML کامنت اضافه نکن. ۲) لنگر پایتونی با `\n` داخل رشته‌ی C# باید `\\n` باشد (splice11b) — assert-before-write درخت را سالم نگه داشت.

**فایل‌ها:** ۹ فایل UI + MainViewModel + StepDefinitions + StepTextsFa + csproj 0.9.25 + TestRunner + docs/persian-full-coverage-v0.9.25.md + CLAUDE-IMPLEMENT-v0.9.25.md.

---

## v0.9.26 — موس روان حین تایپ: مهار با سقف + استراحت‌های کم‌تعداد (2026-09-02)

**گزارش:** در Parallel Group وقتی تایپ شروع می‌شود موس «تکه‌تکه» و با قطع‌ووصل حرکت می‌کند (رکورد کاربر فرستاده شد).

**شواهد (رکورد ۷۲٫۶s اپ با پلن pj6 + رکورد متراکم ۲۰٫۲s دست):**
- اپ: ۷۷ مکث ≥۱۰۰ms حین تایپ؛ ۱۱ فریز ≥۵۰۰ms؛ دو فریز میان‌مسیر **۱۲٫۴s و ۱۱٫۰s** در حالی که ۸۲ و ۷۶ ضربه‌ی کلید در همان بازه‌ها با کادنس عادی رد شدند → کانال سریال سالم بود؛ شاخه‌ی موس در یک await طولانی پارک شده بود. هر دو فریز با همان پیکسل (±۳px) شروع و تمام شدند = تاخیرهای کشیده روی نقاط زیرپیکسل دمِ مسیر.
- دست: حین تایپ p90 گپ موس ۶ms، حداکثر ۳۵۱ms، صفر فریز ≥۵۰۰ms.

**ریشه:** ۱) `SuppressedMouseDelayMs` بدون سقف (×۲) — با moveTime تا ۷۰۰۰ms در پلن، تاخیرهای دمِ مسیر ثانیه‌ای دوبرابر می‌شدند. ۲) `MaybeTypingRestAsync` هر ۲–۶ ضربه استراحت ۱۲۰–۵۰۰ms (۱۰٪ تا ۱۲۰۰ms) — پنجره‌ی ۹۰۰msی IsTypingActive در burst پیوسته هرگز نمی‌گذرد پس استراحت‌ها پشت‌سرهم می‌افتادند.

**رفع:** سقف ۱۴۰ms برای مهار (`SuppressedMouseDelayCapMs` — حس نیم‌سرعت حفظ، هیچ تاخیر منفردی ثانیه‌ای نمی‌شود) + کادنس استراحت هر ۱۰–۲۴ ضربه با ۹۰–۳۰۰ms (۱۰٪: ۳۵۰–۷۰۰ms) در `NextTypingRestEveryKeys`/`TypingRestMs` (خالص، تست‌پذیر). همه app-side و pause-aware؛ پروتکل برد و send_path دست‌نخورده.

**چرا مسیر ردشده:** حذف کامل مهار (برگشت به v0.9.21) رد شد — همان «موس بیش‌ازحد فعال» بود (p90 تأخیر موس-بعد-از-کلید 43ms در برابر 982ms انسانی). نیم‌سرعتِ با سقف هر دو داده را ارضا می‌کند.

**تست:** گام ۲۶ — ۷ assertion (سقف، کادنس ۱۰–۲۴، طول ۹۰–۷۰۰، نرخ ~۱۰٪). گام ۲۳ دست‌نخورده (assertهایش زیر سقف‌اند).

**درس فرایندی:** مهار رفتاری بدون سقف روی ورودی کنفیگ‌شدنی (moveTime تا ۷۰۰۰ms) = بمب زمانی؛ هر ضریب روی زمان‌بندی کاربر باید clamp داشته باشد. رکورد متراکم دست (p90 گپ ۶ms حین تایپ) معیار قطعی «روان‌بودن» شد — انسان حین تایپ موس را نمی‌پارکد، فقط گاهی بین حرکت‌ها می‌نشیند.

**فایل‌ها:** RunEngine.cs (SuppressedMouseDelayMs + SuppressedMouseDelayCapMs + MaybeTypingRestAsync + NextTypingRestEveryKeys + TypingRestMs)، بنر v0.9.26، csproj 0.9.26، TestRunner گام ۲۶، docs/mouse-typing-glide-v0.9.26.md، CLAUDE-IMPLEMENT-v0.9.26.md.

---

## v0.9.27 — صدای فوری در Parallel Group: MediaPlayer روی Dispatcher (2026-09-02)

**گزارش:** در پلن 2.amsj (تایپ موازی + findImage → playAudio) آهنگ با تاخیر ۵–۱۰ ثانیه پخش شد؛ هیچ Delayای تنظیم نشده بود.

**حذف مسیرهای بی‌گناه (داده/کد):** نگاشت کمبوی timeoutUnit سالم است (`ms→0, second→1, minute→2, hour→3` هر دو جهت) — `timeoutUnit: "ms"` در فایل واقعی است، regression ترجمه‌ی v0.9.25 نیست. با timeout=80ms تصویر باید همان poll اول پیدا شده باشد (وگرنه صدا هرگز نمی‌آمد) → تاخیر در vision نبوده. polling تطبیقی حداکثر ~۴۰۰ms است.

**ریشه:** thread-affinity ـی `MediaPlayer`. مسیر ترتیبی روی UI thread ادامه می‌یابد (await + SynchronizationContext) ولی شاخه‌های Parallel Group با `Task.Run` روی thread-pool بدون Dispatcher pump می‌روند → `Open/Play` ثانیه‌ها گیر می‌کند و `MediaEnded` هرگز fire نمی‌شود (loop شکسته + نشت پلیر غیرلوپ تا پایان run).

**رفع:** همه‌ی کارهای پلیر (ساختن، Open، Play، اتصال MediaEnded) داخل `Application.Current.Dispatcher.Invoke`؛ `StopAllAudio` هم مارشال می‌شود + نگهبان HasShutdownStarted (هنگام خروج اپ Invoke همزمان hang نکند — sweep مستقیم fallback). مسیر ترتیبی بدون تغییر رفتار.

**چرا مسیر ردشده:** جابه‌جایی کل RunEngine روی UI thread رد شد — engine باید background بماند (لاگ/پاسخ‌گویی)؛ فقط مالکیت پلیر به UI سپرده شد. راه‌حل جایگزین آینده در صورت نیاز: نخ STA اختصاصی صدا با Dispatcher.Run.

**تست:** گام ۲۷ — ۵ assertion نگهبان فایلی (الگوی گام ۲۵). گام‌های قبلی دست‌نخورده.

**درس فرایندی:** هر ساخت/لمس WPF object با affinity (MediaPlayer، MediaElement، DispatcherObject) باید روی نخ دارای pump باشد؛ «روی کدام نخ ادامه می‌یابد؟» را هنگام افزودن قابلیت به شاخه‌های موازی بپرس — await روی UI شروع می‌شود ولی Task.Run در runner موازی آن را می‌شکند.

**فایل‌ها:** RunEngine.cs (کیس playAudio + StopAllAudio)، بنر v0.9.27، csproj 0.9.27، TestRunner گام ۲۷، docs/audio-dispatcher-v0.9.27.md، CLAUDE-IMPLEMENT-v0.9.27.md.

---

## v0.9.28 — تشخیص فوری تصویر: گرم‌کردن vision + دور اول همیشه‌جست‌وجو (2026-09-02)

**گزارش:** با پلن 2.amsj جدید صدا ~۱۵ ثانیه بعد از دیده‌شدن تصویر پخش شد، حتی بعد از v0.9.27 («انگار توی صف می‌ره»).

**شواهد:** diff پلن قدیم→جدید: `searchScope: region(338×108) → entireScreen`. تاخیر ران قدیم (۵–۱۰s) صدا-سمت بود (MediaPlayer بدون pump — رفع v0.9.27)؛ تاخیر ران جدید vision-سمت است. تایپ آزادانه جریان داشت → صفی در کار نبود.

**ریشه:** در entireScreen هر دور جست‌وجو = ۴ نوار تمام‌صفحه × (کپچر GDI + دو انتگرال‌ایمیج + NCC هرمی + refine ≤۸ کاندید) و دور **اول** هزینه‌ی سرد دارد: tier-0 JIT کل مسیر داغ + تخصیص LOH + اولین کپچر — جمعاً ~۱۵s. تایم‌اوت (effectiveTimeout = timeoutMs/0.7) فقط **بین** دورها چک می‌شد و skip تصادفی ۳۰٪ (action 2) می‌توانست قالب را از دور اول حذف کند.

**رفع:** ۱) `VisionService.Warmup()` — self-match مصنوعی ۹۶×۶۴/۳۶×۳۶ با Random(28) که کل مسیر داغ را در ابتدای RunAsync گرم می‌کند ۲) skip فقط بعد از دور اول (`polls > 0 &&`) ۳) چک ct + تایم‌اوت بین نوارها (Stop/timeout وسط دور سنگین گیر نمی‌کند) ۴) لاگ `poll round N took X ms` برای شواهد ران بعدی.

**چرا مسیر ردشده:** بازنویسی عمیق matcher برای reuse فریم/انتگرال بین قالب‌ها و نوارها رد شد — بدون اجرای ویندوزی قابل‌اعتماد نیست و ریسک رگرسیون روی پرتست‌ترین زیرسیستم (گام‌های ۱۹–۲۰) بالاست؛ اول شواهد زمان‌بندی هر دور با لاگ جدید، بعد بهینه‌سازی هدفمند.

**تست:** گام ۲۸ — ۵ assertion (Warmup اجرایی واقعی + ۴ نگهبان فایلی). گام‌های قبلی دست‌نخورده. اصلاح MediaEnded-scope ـی Claude Code در TestRunner مرج شد.

**درس فرایندی:** هزینه‌ی سرد (cold JIT/alloc) را در تحلیل تاخیر جدی بگیر — الگوریتم گرم sub-second بود، سرد ۱۵s. و: diff فایل پلن بین دو ران، ارزان‌ترین ابزار تشخیص است؛ اول آن را بخوان.

**فایل‌ها:** VisionService.cs (Warmup + شرط skip + چک‌های نوار + لاگ دور)، RunEngine.cs (فراخوانی Warmup در RunAsync)، بنر v0.9.28، csproj 0.9.28، TestRunner گام ۲۸، docs/vision-warmup-v0.9.28.md، CLAUDE-IMPLEMENT-v0.9.28.md.

---

## v0.9.29 — دیالوگ لوپ شفاف + زنده‌شدن برچسب‌های فارسی per-step (2026-09-02)

**گزارش:** اسکرین‌شات دیالوگ For Loop — فیلدهای count و time در هر سه حالت فعال؛ «اگه ۱۰ دقیقه بدون محدودیت، پس چرا دو فیلد؟ تناقضه».

**پاسخ مفهومی:** تناقض رفتاری نیست — `mode` قانون را انتخاب می‌کند (count = تعداد بار / time = timeValue×timeUnit / infinite = تا Stop با Shift+F2) و فیلدهای دیگر خنثی‌اند؛ مشکل نمایش همیشگی همه بود.

**باگ ۱ — نمایش شرطی لوپ:** ماشینری v0.9.14 فقط «پنهان وقتی مساوی» (HideWhenValue) داشت؛ لوپ سه قانون دارد و count باید در دو حالت پنهان شود. رفع: `HideUnlessValue` در FieldDef (پارامتر اختیاری انتهایی رکورد — call siteهای قدیمی نشکستند) + فایل جدید `Models/StepFieldVisibility.cs` با `FieldVisible(depValue, hideWhen, hideUnless)` خالص و تست‌پذیر + اعمال در ApplyConditionalVisibility. قواعد: count → HideUnlessValue="count"، timeValue/timeUnit → "time"؛ infinite همه را پنهان می‌کند.

**باگ ۲ — برچسب‌های per-step مرده (از v0.9.24!):** `_stepType = FindTypeByFields(fields)` روی آرایه‌ی **الحاق‌شده** (فیلدهای استپ + __name/__delay/__delayMax) صدا زده می‌شد و reference-match هیچ‌وقت اتفاق نمی‌افتاد → `_stepType` همیشه null → کل `FaByStep` (mode/text/path/x/y/w/h/label…) بی‌صدا fallback انگلیسی می‌گرفت. sweep گام ۲۵ دیکشنری را مستقیم تست می‌کرد نه مسیر دیالوگ را — برای همین جاماند. رفع: پارامتر صریح `stepType` در ctor دیالوگ از MainViewModel (`type` در scope بود) + fallback قدیمی برای دیالوگ ویرایش گروهی.

**فارسی‌سازی پوسته:** `__name`/`__delay`/`__delayMax` به دیکشنری عمومی Fa اضافه شد («نام استپ» / «تأخیر بعد از استپ (ms)» / توضیح فارسی delayMax) — فیلدهای مشترک همه‌ی دیالوگ‌ها که انگلیسی مانده بودند.

**تست:** گام ۲۹ — ۶ assertion (FieldVisible سه‌حالته + رفتار v0.9.14 ثابت + برچسب‌های پوسته + حل‌شدن forLoop:mode به فارسی + نگهبان پاس صریح stepType).

**درس فرایندی:** ۱) sweep روی داده، بدون تست مسیر مصرف‌کننده‌ی واقعی، حفره‌ی پوشش می‌سازد — نگهبان فایلی برای call site بگذار. ۲) resolution بر پایه‌ی reference equality روی آرایه‌های مشتق‌شده بمب خاموش است؛ شناسه‌ی صریح بفرست.

**فایل‌ها:** StepDefinitions (HideUnlessValue + قواعد لوپ)، StepFieldVisibility.cs (جدید)，StepDialog (stepType صریح + قاعده‌ی جدید)، StepTextsFa (۳ کلید پوسته)، MainViewModel (پاس type + بنر)، csproj 0.9.29، TestRunner گام ۲۹، docs/loop-dialog-clarity-v0.9.29.md，CLAUDE-IMPLEMENT-v0.9.29.md.

**ریلیز:** `Classroom-Studio-v0.9.29-release.zip` (۲۴۳۶ KB، ۸ فایل: exe+dll+deps+bridge.py) در Downloads ✅
**تست‌ها:** ۳۲۶/۳۲۶ پاس — گام ۲۹: ۶ assertion (FieldVisible سه‌حالته + v0.9.14 unchanged + پوسته فارسی + stepType صریح)

**ریلیز:** `Classroom-Studio-v0.9.30-release.zip` (۲۴۳۸ KB، ۸ فایل: exe+dll+deps+bridge.py) در Downloads ✅
**تست‌ها:** ۳۲۴/۳۲۴ پاس — گام ۳۱: ۵ assertion (WSND vs TRGSND + bool heard + findImage|waitForSound + insertIfElse hide)

**ریلیز:** `Classroom-Studio-v0.9.31-release.zip` (۲۴۳۸ KB، ۸ فایل: exe+dll+deps+bridge.py) در Downloads ✅
**تست‌ها:** ۳۱۷/۳۱۷ پاس — گام ۳۰: ۸ assertion (Snapshot round-trip + Parent rewire + LocateElseBlock ۴ حالت + Snapshot/Uncro infrastructure + KeyBinding wires)

**ريليز:** `Classroom-Studio-v0.9.32-release.zip` (۲۴۳۸ KB، ۸ فایل: exe+dll+deps+bridge.py) در Downloads ✅
**تست‌ها:** ۳۳۴/۳۳۴ پاس — گام ۳۲: ۵ assertion (SCAL path kept + WSND fallback exists + floor report + label text + csproj version)

**ريليز:** `Classroom-Studio-v0.9.32-release.zip` (۲۷۰۰ KB، ۸ فایل: exe+dll+deps+bridge.py+NAudio) در Downloads ✅
**تست‌ها:** ۳۳۰/۳۳۰ پاس — گام ۳۲: ۵ assertion (SCAL path + WSND fallback + floor report + label text + csproj version)
**تغییرات صوتی:** NAudio 2.2.0 اضافه شد → playAudio فیلد outputDevice (0=پيش‌فرض، -1=خودکار) + WaveOutEvent به جای MediaPlayer

**ريليز:** `Classroom-Studio-v0.9.32-release.zip` (۲۷۰۰ KB، ۸ فایل: exe+dll+deps+bridge.py+NAudio) در Downloads ✅
**تست‌ها:** ۳۳۰/۳۳۰ پاس
**ویژگی‌های جدید:** ۱) نشانگرهای ساختاری Else/EndIf حذف‌ناپذیر هنگام insertIfElse=true · ۲) Toggle آکاردئون برای Else · ۳) فیلد outputDevice برای playAudio (NAudio WaveOutEvent)

**ريليز:** `Classroom-Studio-v0.9.33-release.zip` (۲۶۷۴ KB، ۸ فایل) در Downloads ✅
**تست‌ها:** ۳۳۱/۳۳۱ پاس — گام ۳۳: ۵ assertion (LoopableOutput + StopRequested + using default + or "waitForSound" >= 3 + label fix)

**ريليز:** `Classroom-Studio-v0.9.34-release.zip` (۲۶۷۴ KB، ۸ فایل) در Downloads ✅
**تست‌ها:** ۳۳۲/۳۳۲ پاس — گام ۳۴: ۵ assertion (IsContainer/IsScopeContainer + ShowToggle + EnsureElseMarkers idempotent + End If guard + deeper nesting)
**اصلاحات tree accordion:** waitForSound IsContainer+IsScopeContainer = آکاردئون روی ردیف If · نشانگرهای Else/EndIf محافظت‌شده · تو‌در‌تویی عمیق‌تر (۲۲px)

**ريليز:** `Classroom-Studio-v0.9.35-release.zip` (۲۶۷۵ KB، ۸ فایل) در Downloads ✅
**تست‌ها:** ۳۴۲/۳۴۲ پاس — گام ۳۵: ۵ assertion object-level (HasElseMarkersForUi + SanitizeElseMarkers + IsStructuralMarkerIn + orphan protection)
**درس:** EnsureElseMarkers نباید از LocateElseBlock (موتور اجرا) استفاده کند؛ این ابزار برای UI ساخته نشده (non-comment را می‌شکند). HasElseMarkersForUi اختصاصی UI باید ساخت.

**ريليز:** `Classroom-Studio-v0.9.35-release.zip` (۲۶۷۵ KB، ۸ فایل) در Downloads ✅
**تست‌ها:** ۳۴۳/۳۴۳ پاس — گام ۳۵: ۶ assertion (Add: line 1364 red scope margin 22px)
**درس:** موقعیت خط قرمز scope (MarkRange) جدا از Margin/Indent FlatStepRow است؛ هر دو باید ۲۲px باشند.

## v0.9.44 (2026-09-04)
**محور:** ۵ مورد گزارش کاربر — زیرمنوی ریل با کنار رفتن موس بسته می‌شود (MouseLeave + تأخیر ۴۰۰ms + نگهبان IsMouseOver + ReferenceEquals) · رگ قرمز parallelGroup (Renumber: opensParallel + نگهبان IsScopeMarker تا End If ِ والد قورت نشود) · خروجی پیکو به گزینه‌های پخش احترام می‌گذارد (LOOP_MODE/LOOP_COUNT/LOOP_SECONDS در code.py + loop_due؛ پارامترهای اختیاری Export با پیش‌فرض forever) · LED جداگانه برای پیکو و پرو میکرو در نوار وضعیت (پروب PING بعد از اتصال + ParseBoardPresence) · انتخاب برد مجری کیبورد در Options (KeyboardBoard=pico/promicro) — code.py حالا KTEXT/KCOMBO/KDOWN/KUP را محلی اجرا می‌کند یا با KBD_ON_ARM به بازو فوروارد می‌کند (MOD_VK برای مدیفایرها؛ تایم‌اوت KTEXT متناسب با طول متن) · BundleVersion → 0.9.44.
**تست‌ها:** گام ۴۴ با ۱۶ assertion (کل Assert( = ۴۲۷) — انتظار 464/0 (۴۴۸ اجراشده‌ی v0.9.43 + ۱۶).
**بازبینی ریلیز v0.9.43 کاربر:** اصیل (هر ۹ نشانه بایتی در DLL · bridge.py = e72530b2 · تست 448/0).
**درس (سخت‌گیرانه‌تر):** ریست سندباکس وسط زنجیره‌ی پچ بخش A+B را برگرداند — قاعده: بعد از هر بخش پچ همان فراخوانی verify کن؛ و الگوی «cmd || cat > script» فقط بازسازی می‌کند و اجرا نمی‌کند — جدا اجرا کن.


## v0.9.45 (2026-09-05)
**محور:** رفع قطعی flicker/crash منوی ریل با حذف بازکردن مستقیم ContextMenu در MouseEnter و حذف async-void/Task.Delayهای رقیب؛ state machine تک‌مالک با dwell 220ms + watcher 120ms و ناحیه‌ی مشترک host/menu. گزینه‌ی انتخاب برد مجری کیبورد که در ردیف افقی 420px کلیپ می‌شد به تب مستقل «تقسیم کار بردها» در Options 500px منتقل شد. برای هر For Loop نشانگر ساختاری و محافظت‌شده‌ی `# Next` اضافه شد: Add/Edit/Paste ایجاد، Open/Import ترمیم بازگشتی و idempotent، Loop+Next واحد اتمیک Delete/Cut/Copy، و انتهای رگ روی Next.
**تست‌ها:** گام ۴۵ با ۱۵ assertion؛ کل `Assert(` = ۴۴۲؛ انتظار 480/0 بر پایه‌ی build واقعی v0.9.44 با 465/0.
**بازبینی v0.9.44:** ریلیز اصیل؛ bridge.py = e72530b2…؛ سورس 64.zip دارای Version 0.9.44 و خروجی تازه‌ی 465/0.
**درس:** ContextMenu یک Popup/HWND جداست؛ بازکردن هم‌زمان با MouseEnter capture را عوض می‌کند و Enter/Leave بازگشتی می‌سازد. برای popup ها باز/بسته‌کردن باید state machine تک‌مالک، idempotent و مبتنی بر dwell/poll ناحیه‌ی host+popup باشد، نه چند async delay.


## v0.9.46 (2026-09-05)
**محور:** بسته‌نشدن popup ریل در v0.9.45 با علت دقیق‌تر حل شد: `ContextMenu.IsMouseOver` در Popup/HWND جدا می‌توانست تا کلیک بعدی stale بماند؛ watcher اکنون مختصات واقعی `Control.MousePosition` را با مستطیل screen-space آیکون و منو (`PointToScreen`) مقایسه می‌کند. انتخاب برد مجری به چهار استپ کیبورد افزوده شد (`default/pico/promicro`): default قانون کلی Options را حفظ می‌کند؛ انتخاب صریح با envelopeهای `KBDPICO|`/`KBDARM|` به firmware پیکو می‌رود؛ اتصال مستقیم Pro Micro مسیر arm را unwrap می‌کند و انتخاب Pico بدون حضور Pico خطای روشن می‌دهد. code.py هر دو envelope را قبل از handle/forward مصرف می‌کند. متن `# Next` با `SummaryInset=12px` داخل‌تر شد بدون تغییر depth/شماره‌گذاری/انتهای رگ.
**تست‌ها:** build واقعی v0.9.45 = 484 پاس / 1 فیل؛ فیل فقط assertion متنی کهنه‌ی v0.9.37 بود (`loopHealed` به شرط dirty اضافه شده بود). ترمیم شد. گام ۴۶: ۱۵ خط Assert و ۱۸ assertion اجرایی؛ کل خطوط Assert = ۴۵۷؛ انتظار 503/0.
**درس:** برای Popup جداگانه به `IsMouseOver` اعتماد نکن؛ خروج واقعی را با cursor screen coordinates و مستطیل هر دو HWND/Visual بسنج. برای override سخت‌افزار per-step، حالت `default` را جهت backward compatibility نگه دار و routing metadata را در مرز transport unwrap/validate کن.

## v0.9.47 (2026-09-05)
**محور:** گزارش کاربر — متن `# Next` باید بیرون‌تر و هم‌تراز سر مجموعه باشد. `SummaryInset` ۱۲پیکسلی v0.9.46 حذف شد (هم property در FlatStepRow هم binding در قالب ردیف). هم‌ترازی ساختاری است و مارجین لازم ندارد: Next خواهرِ حلقه است ⇒ همان Depth و همان `Indent = Depth*22`؛ و ستون toggle درون `RowTextAnchor` عرض ثابت ۱۴px دارد که حتی با toggle پنهان رزرو می‌ماند ⇒ `SummaryText` همه‌ی ردیف‌ها از یک x شروع می‌شود. شماره‌گذاری، depth، سلسله‌مراتب و انتهای رگ دست نخورد.
**تست‌ها:** گام ۴۷ با ۹ assertion قطعی؛ دو assertion ِ inset در گام ۴۶ به حالت retracted بازنویسی شد؛ کل `Assert(` = ۴۶۶.
**بازبینی v0.9.46:** ریلیز اصیل (FileVersion 0.9.46.0 · bridge.py = e72530b2… · سورس بایت‌به‌بایت برابر درخت 65.zip) و تست واقعی 495/0.
**درس (مهم):** عدد کل تست‌ها deterministic نیست — حلقه‌ی `seed < 40 && !(sawMerged && sawSplit)` در TestRunner.cs خروج زودهنگام دارد و هر اجرا تعداد متفاوتی assertion می‌سازد (۷، ۸، ۱۳، ۵ در v0.9.43 تا v0.9.46). ملاک پذیرش = `0 failed` + حضور همه‌ی assertionهای گام جدید، نه یک عدد کل دقیق.
**درس UI:** برای هم‌ترازی دو ردیف هم‌سطح، مارجین موردی اضافه نکن؛ اول ببین قالب ردیف با Depth و ستون‌های عرض‌ثابت خودش هم‌ترازی را تضمین می‌کند یا نه.
**درس پچ (دو بار تکرار شد):** ۱) پیش از assert روی تعداد تکرار، تجربی بشمار — من ۲ حدس زدم و مارکر نسخه در TestRunner ۱۳ بار بود (۱۳ csproj · ۱۱ بنر · ۲ BundleVersion) چون هر گام نسخه‌ی جاری را pin می‌کند. ۲) ریست سندباکس باز هم نوشتن TestRunner را بلعید — پس هر پچ باید idempotent باشد و در همان اجرا از روی دیسک verify شود.

## v0.9.48 (2026-09-05)
- محور: قانون سراسری «هر بخشی که زیرمجموعه می‌گیرد، # Next دارد» گسترش یافت به parallelGroup و randomPackage (همان معماری v0.9.45 + helper واحد `OwnsNextMarker`) · درگ اتمیک بلوک+Next با moveSet · اسکرول خودکار لبه‌ها هنگام درگ (ریشه‌ی «درگ از پایین به بالا نمی‌رود»: ListBox هنگام DragDrop اسکرول نمی‌کند) · هدف‌گذاری drop روی ردیف‌های نشانگر — هیچ drop نمی‌تواند نشانگر را از سرش جدا کند (before/into روی Next/End If = ته شاخه‌ی آخر بلوک · بالای Else = ته Then · زیر Else = اول Else · زیر سر بلوک = اولین فرزند · بعد از نشانگر بسته = بعد از کل بلوک) · تب‌های تنظیمات Collapsed شدند — **ریشه‌ی «تب طویل و بهم‌ریخته»: Visibility.Hidden همچنان فضای layout اشغال می‌کند** و پنجره با SizeToContent=Height به مجموع هر چهار تب می‌رسید · تب نقش بردها به دو کارت بازطراحی شد.
- درس‌ها: Hidden ≠ نامرئی در layout — برای پنل‌های تب‌مانند همیشه Collapsed · assertion قدیمی که رفتار معکوس‌شده را pin کرده باید retraction بازنویسی شود نه حذف (گام ۴۴: قانون «parallelGroup نشانگر ندارد») · در DnD هر باند (بالا/وسط/پایین) × هر نوع ردیف (سر/نشانگر/ساده) باید معنای شفاف داشته باشد · درگ container بدون نشانگرش = نقض قرارداد — moveSet الگویی شد.
- تست: Assert( ‏466 → 479 · گام ۴۸ با ۱۳ assertion قطعی · پذیرش build: 0 failed + ۱۳ خط PASS گام ۴۸ (عدد کل به‌خاطر sweep تصادفی غیرقطعی است) · نسخه‌ها: csproj/banner/BundleVersion = 0.9.48.

## v0.9.49 (2026-09-05)
- محور: رفع no-op ِ drop روی باند میانی ردیف ساده (گزارش کاربر با اسکرین‌شات: Key Down روی Type text نمی‌رفت بالا، برعکسش می‌شد) — ریشه: fallback ِ "into" روی ردیف غیرکانتینری به `i+1` = همان جای فعلی ⇒ برای ردیف بلافاصله پایینی همیشه no-op · اصلاح دولایه: باندهای 50/50 برای ردیف ساده در view + `DropBeforeForPlainRow` (جهت‌آگاه: بالا = before، پایین = after) در MoveNode با capture ِ ایندکس‌ها پیش از removal · دیالوگ تنظیمات به لبه‌ی راست پنجره‌ی اصلی dock می‌شود (CenterOwner شناور بود؛ Owner + ShowDialog از قبل بود) با دکمه‌های چسبیده به پایین · درس: هر fallback برای «into» روی هدف غیرکانتینری باید جهت درگ را بداند، وگرنه برای همسایه‌ی مجاور no-op می‌شود · درس دوم: CenterOwner + پنجره‌ی جمع‌شده = حس «کارت شناور» — dock به لبه‌ی owner حس «متصل» می‌دهد.
- تست: Assert( ‏479 → 489 · گام ۴۹ با ۱۰ assertion قطعی (۵ رفتاری شامل دقیقاً همان کیس گزارش‌شده) · پذیرش build: 0 failed + ۱۰ خط PASS گام ۴۹ (عدد کل به‌خاطر sweep تصادفی غیرقطعی است) · نسخه‌ها: csproj/banner/BundleVersion = 0.9.49.

## v0.9.50 (2026-09-05)
- محور: ادغام ابزار مستقل AMS USB Studio v3 به‌عنوان پنجره‌ی «آماده‌سازی برد» داخل اپ (Tools → Board Preparation) — نه با الصاق EXE: منطق به C# پورت شد (BoardHexService = پچ Intel HEX و descriptorها با آفست‌های ثابت 0x7EE2/0x7F00 · BoardsTxtService = بلوک مارکردار boards.txt + پکیج Sketchbook بدون ادمین · BoardCheckupService = اسکن VID/PID از رجیستری ویندوز بدون پکیج اضافه + هندشیک) و فقط isp_flash.py مثل bridge.py همراه اپ ماند (ریسک brick ⇒ پورت نه). چهار تب: ساخت HEX با سریال یکتا / نصب برد در IDE / فلش ISP با خروجی زنده / چکاپ فقط‌خواندنی.
- تصحیح‌های آگاهانه نسبت به ابزار اصلی (مستند در docs): هندشیک چکاپ از «001|HELLO|» به قالب واقعی firmware 1.6 «HELLO|<32hex>» رسید (ابزار اصلی هرگز جواب نمی‌گرفت) · پیام سریال خالی U+FFFD داشت و ترمیم شد · نام برد = Classroom Studio Board.
- وابستگی تازه: System.IO.Ports 8.0.0 (restore خودکار با build). bridge.py دست‌نخورده (e72530b2…). تنظیمات پنجره: board-prep-settings.json کنار exe.
- درس: پورت وفادار = ابتدا بایت طلایی از ابزار اصلی با ورودی ثابت، بعد assert هش در TestRunner (قاعده‌ی ۳ در مقیاس باینری). درس دوم: چکر ساده‌ی توازن براکت روی PicoFirmwareExporter مثبت‌کاذب می‌دهد (قالب code.py با `[` داخل رشته‌ی verbatim) — با نسخه‌ی پچ‌نشده مقایسه کن پیش از آنکه باگ گمان کنی.
- تست: Assert( ‏489 → 506 · گام ۵۰ با ۱۷ assertion (دو sha256 طلایی HEX + یک sha256 طلایی بلوک برد + idempotency نصب/حذف + ۶ خطای اعتبارسنجی + دسته‌بندی + bundle) · پذیرش build: 0 failed + هر ۱۷ خط PASS گام ۵۰ (عدد کل به‌خاطر sweep تصادفی غیرقطعی است) · نسخه‌ها: csproj/banner/BundleVersion = 0.9.50.

## v0.9.50a (2026-09-05) — هات‌فیکس XAML
- محور: شکست build اولیه‌ی v0.9.50 با `error MC3072` در BoardPrepWindow.xaml خط ۱۳۹ — `TextWrapping="Wrap"` مستقیم روی دو `RadioButton` نوشته شده بود، در حالی که TextWrapping در WPF فقط پراپرتی TextBlock/TextBox است. اصلاح: انتقال متن به `<RadioButton.Content><TextBlock TextWrapping="Wrap"/></RadioButton.Content>`؛ code-behind فقط IsChecked می‌خواند پس بی‌خطر. شماره‌ی نسخه همان 0.9.50 ماند (روش v0.9.39a) و هیچ فایل دیگری دست نخورد (diff با زیپ تحویلی = فقط همین یک فایل + مستندات).
- درس: Parse ِ XML خطای معنایی پراپرتی XAML را نمی‌گیرد — فایل XAML تازه به سوییپ «attribute به‌ازای تگ» نیاز دارد، نه فقط well-formedness. در MC3072 شماره‌ی خط انتهای بلاک المنت است نه محل attribute. سوییپ هم‌خانواده PASS: صفر TextWrapping غیرمجاز در پروژه · هر ۲۳ هندلر موجود · همه‌ی StaticResourceها تعریف‌شده · x:Class مطابق.

## v0.9.50b (2026-09-05) — هات‌فیکس دوم: CS0246 ToggleButton
- محور: بیلد دوم با `error CS0246` روی `ToggleButton` در BoardPrepWindow.xaml.cs:103 شکست خورد — فایل فقط `using System.Windows.Controls` دارد و ToggleButton در `System.Windows.Controls.Primitives` است (implicit usings ِ WPF شامل Primitives/Threading نمی‌شود؛ خطا از v0.9.50 اصلی بود و پشت MC3072 پنهان شده بود). اصلاح: پارامتر ShowPanel به `System.Windows.Controls.Primitives.ToggleButton` fully-qualified شد — فقط یک خط. سوییپ «تایپ → namespace» روی هر ۴ فایل تازه‌ی C# صفر مورد یافت (مثبت‌کاذب: Dispatcher=پراپرتی ارثی DispatcherObject · Handshake=نام متد اعلان‌شده). امضای هر ۲۳ هندلر XAML با نوع رویداد تطبیق داده شد. نسخه همان 0.9.50 · diff با زیپ v0.9.50 = دقیقاً ۲ فایل (xaml + xaml.cs) + مستندات.
- درس: فایل C# تازه هم سوییپ معنایی می‌خواهد: «هر تایپ Capitalized باید از usingهای فایل یا implicit usings بیاید» — تکمیل درس 50a درباره‌ی XAML. ترتیب build در WPF: MarkupCompilePass1 → CoreCompile → MarkupCompilePass2؛ خطای XAML زودتر، خطاهای تایپ C# را ماسک می‌کند.

## v0.9.50c (2026-09-05) — هات‌فیکس سوم: using System.IO در سه سرویس
- محور: بیلد 50b با ۴۷ خطا (CS0103/CS0246 روی Path/File/Directory/DirectoryInfo/InvalidDataException) متوقف شد — سه سرویس تازه‌ی Board*.cs فقط System.Text داشتند. تحلیل محیطی: روی ماشین کاربر System.IO به‌صورت implicit در دسترس نیست (با وجود ImplicitUsings=enable در csproj) — شاهد: هر ۸ فایل قدیمی پروژه `using System.IO;` صریح دارند و پنجره در همان بیلد کامپایل شد. اصلاح: بلاک using کامل و صریح به سه سرویس اضافه شد (System · Collections.Generic · IO · Linq · Threading برای چکاپ)؛ توکن‌های مبهم چشمی رد شدند (Key = پارامتر record). نسخه همان 0.9.50 · diff با زیپ v0.9.50 = دقیقاً ۵ فایل سورس (۲ پنجره + ۳ سرویس) + مستندات.
- درس: فرض سوییپ باید از قرارداد کدبیسِ در حال کامپایل بیاید نه مستندات SDK — implicit usings قابل‌اتکا نیست؛ قاعده‌ی تحویل: هر فایل .cs تازه using صریح برای همه‌ی namespaceهای مصرفی‌اش می‌خواهد (صفر-implicit فرض شود). رشته‌ی شکست‌های 50a→b→c همه از یک کلاس بودند: فایل‌هایی که هرگز build واقعی ندیده بودند.

## v0.9.51 (2026-09-05) — پاکسازی تاریخچه‌ی COM + کارت مشخصات + راست‌چین
- محور: چکاپ برد ۲۱ پورت نشان می‌داد با یک برد وصل — تاریخچه‌ی Enum\USB با زنده‌ها مخلوط بود و پروگرمرهای مرده «آنلاین» گزارش می‌شدند. قاعده‌ی فانتوم: در Enum\USB هست ولی در DEVICEMAP\SERIALCOMM نیست (تفکیک بدون ادمین، چون هر دو از قبل خوانده می‌شدند). PortInfo ← IsPhantom/RegPath · چکاپ برای فانتوم HELLO نمی‌فرستد · خلاصه فقط زنده‌ها را می‌شمارد · ردیف تاریخچه نشان 🕘 دارد (DescribePort به سرویس کوچید). پاکسازی: دکمه‌ی 🧹 با dry-run + تأیید صریح ← request JSON ← relaunch خودِ exe با Verb=runas و حالت headless در App.OnStartup ← بکاپ reg.exe ← take ownership با SID ِ S-1-5-32-544 (زبان‌مستقل) ← DeleteSubKeyTree ← آزادسازی بیت ComDB فقط برای حذفشده‌ها ← com-cleanup-result.log. نگهبان‌ها: allow-list VID/PID · فقط Enum\USB · بازچک «هنوز فانتوم» در لحظه‌ی اجرا · بدون بکاپ هیچ حذفی نیست.
- کارت «مشخصات برد» ابزار اصلی در پورت جا مانده بود ← برگشت (TxtBoardSpecs همگام با تب ۱). راست‌چین فارسی در پنجره‌ی آماده‌سازی: هر TextBlock فارسی TextAlignment="Right" + آیتم‌های خلاصه راست‌چین — گام ۵۱ قفلش می‌کند (قرارداد v0.9.24).
- درس: stripper توازن باید رشته‌ی verbatim را اول بردارد (@"HKLM\")؛ درس v0.9.32 دوباره تأیید شد (بلاک RTL اول با کوتیشن escape‌شده شکست ← با char literal بازنویسی شد). درس دیگر: diff نسخه باید با آخرین تحویل (50c) مقایسه شود، نه مبنای قدیمی — وگرنه حمل‌تغییرات هات‌فیکس‌ها «فراتر از انتظار» به نظر می‌رسد.
- تست: گام ۵۱ با ۱۶ assertion · Assert( ‏506 → 522 · نسخه‌ها: csproj/banner/BundleVersion = 0.9.51.

## v0.9.51a (2026-09-06) — هات‌فیکس CS1009 در تست
بیلد اپ ۰ خطا ✅ ولی تست: CS1009 خط ۲۹۱۰ TestRunner — پیام assertion حاوی Enum\USB در رشته‌ی غیر-verbatim بود (تولید لایه‌ای یک سطح بک‌اسلش خورد؛ درس v0.9.32 بار سوم). اصلاح: همان خط @"…". چک تحویل تازه: سوییپ «escape نامعتبر در رشته‌ی غیر-verbatim» روی همه‌ی فایل‌های دست‌خورده (۱ مورد یافت و بسته شد).


## v0.9.52 — ویزارد، RTL، دستگاه‌های آموزشی، hot-plug

- `Services/HotPlugWatcher.cs` (جدید) + تایمر ۱٫۵ثانیه در `MainViewModel`: بردی که بعد از اجرای برنامه وصل شود، خودکار وصل و سبز می‌شود.
- `BoardPrepWindow`: تب‌ها ← قدم‌های شماره‌دار با آیکون برداری، نوار حرکت قدم قبل/بعد، کارت مشخصات در قدم ۱، پنجره RTL و ۱۴ کنترل فنی LTR.
- شش هویت آموزشی: microbit2 / calliope / picoedu / circuitplay / legospike / m5stack (جفت بوت+اپ در چکاپ).
- تست: گام ۵۲ با ۱۸ ادعا؛ پین‌های نسخه به 0.9.52 منتقل شد.
- درس: برای فارسی، `TextAlignment` کافی نیست؛ `FlowDirection` سطح پنجره لازم است و کنترل‌های مسیر/لاگ باید LTR بمانند.


## v0.9.53 — تشخیص پورت وصل با PnP + نردبان حذف تاریخچه

- **درس ۱:** SERIALCOMM منبع معتبری برای «وصل بودن» نیست (composite/CDC را جا می‌اندازد). منبع درست = PnP (`CM_Locate_DevNodeW` از cfgmgr32) — همان کاری که pyserial در ابزار مرجع می‌کرد.
- **درس ۲:** مسیرهای `Enum\USB` پسوند `&MI_xx` دارند؛ الگوی سختگیرانه همه را رد می‌کند. خانواده باید PID بوت و اپ (±۱) را پوشش دهد.
- **درس ۳:** ادمین بودن برای دست‌زدن به `Enum\USB` کافی نیست؛ باید `SeTakeOwnership`/`SeRestore` را با `AdjustTokenPrivileges` فعال کرد یا از pnputil / تسک SYSTEM رفت.
- پین نسخه → 0.9.53؛ گام ۵۳ = ۲۰ ادعا؛ تست‌های زنجیره‌ای نسخه اصلاح شدند (انتطار: 0 failed).


## v0.9.54 — پیش‌فرض دستگاه‌ها + فرم مشخصات برد + اسکن تمیز

- **درس ۱:** ساده‌سازی نباید هیچ فیلدی را حذف کند؛ فرم مشخصات برد در قدم ۲ بازگشت (معادل تب ۲ ابزار مرجع) و خودکار پر می‌شود.
- **درس ۲:** هر هویت باید مقادیر پیش‌فرض واقعی داشته باشد (`DefaultsFor`)؛ PID اپ = PID بوت + ۱.
- **درس ۳:** لیست پورت نباید تاریخچه‌ی دستگاه‌های دیگران را قاطی کند؛ پیش‌فرض = فقط متصل، تاریخچه پشت تیک اختیاری.
- حذف‌شده‌ها: microbit / microbit2 / calliope / picoedu / circuitplay / esp32. باقی: none / stm32 / xiao / microchip / legospike / m5stack.
- پین نسخه → 0.9.54؛ گام ۵۴ = ۱۹ ادعای برچسب‌دار.


## v0.9.55 - صفحه‌کلیدها + تنظیمات درون‌پنجره + سر مجموعه‌های قابل نام‌گذاری

- بیست هویت صفحه‌کلید (لیست کاربر) با VID رسمی برندها؛ همه CDC (0x02)، PID اپ = بوت + ۱.
- **درس:** هویت‌ها باید تحقیق شوند نه ساخته؛ PID تخمینی باید صریح اعلام و قابل ویرایش بماند.
- تنظیمات دیگر پنجره‌ی جدا نیست: `EmbedContent` + `ShowSettingsPanel`؛ `DialogResult` جای خود را به رویداد `Completed` داد.
- سر مجموعه‌ها فیلد `title` گرفتند و نماد نوع، جلوی عنوان دلخواه می‌ماند تا خاصیت بلوک گم نشود.
- نشانگرها: `next` / `else` / `end if` بدون `#` و ۱۲px نزدیک‌تر به رگ.
- پین نسخه → 0.9.55؛ گام ۵۵.

## ۲۰۲۶-۰۹-۰۸ — v0.9.60 (تجمیع فرم‌ور + هاردنینگ انتقال)

- `code.py` (از طریق `PicoFirmwareExporter`): سنسور BH1750 اختیاری (`ERR|NOSENSOR`) · بافر بایتی کران‌دار · پمپ دائمی بازو در هر تکرار حلقه و داخل انتظارها (ضد back-pressure؛ زنجیره‌ی مرگ ۲۲:۲۲ مورخ ۰۹-۰۷) · موس fire-and-ack · کیبورد همیشه روی Pico و هر دو envelope قدیمی محلی مصرف می‌شوند · کیپد ثابت GP4=Num Lock (Start/Stop) و GP3=Scroll Lock (Pause/Resume) · `AUTOSTART=False` + سکوت ۳ ثانیه‌ای بعد از آخرین فرمان host (ضد اجرای دوبل) · نگهبان never-die.
- `bridge.py`: خروجی UTF-8 never-die (`reconfigure` + فالبک `ensure_ascii=True`) — رفع کرش cp1252 هنگام گزارش خطای واقعی.
- `PythonBoardBridge.cs`: خواندن UTF-8 + `PYTHONIOENCODING` — لاگ فارسی بدون mojibake.
- UI: `SelectionMode="Extended"` برای لاگ سریال · `stableSec` اعشاری کامل (فرمان 500ms + خلاصه‌ی «0.5s» + پارس مستقل از locale).
- تصمیم و ردشده: قالب Options-driven کیپد (v0.9.58d) نگه داشته نشد چون قرارداد سخت‌افزاری نهایی (۰۰:۱۷ بامداد ۰۹-۰۸) کنترل‌های ثابت GP4/GP3 را می‌خواهد؛ `HotkeyToVirtualKeys` به‌عنوان ابزار باقی ماند ولی دیگر در فرم‌ور bake نمی‌شود.
- اعتبارسنجی این‌طرف: شبیه‌سازی سخت‌افزار ساختگی ۲۳/۰ سبز (sim60) + py_compile قالب پرشده + پچ idempotent.
