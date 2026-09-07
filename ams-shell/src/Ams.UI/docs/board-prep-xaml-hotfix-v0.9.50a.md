# v0.9.50a — هات‌فیکس XAML پنجره‌ی آماده‌سازی برد

**رویداد:** اولین build واقعی v0.9.50 با یک خطای XAML شکست خورد:
`error MC3072: The property 'TextWrapping' does not exist ... BoardPrepWindow.xaml, Line 139`.

**ریشه:** `TextWrapping="Wrap"` مستقیماً روی دو `<RadioButton>` (ردیف‌های ۱۳۷ و ۱۴۰ —
`RadioSketchbook` و `RadioBoardsTxt`) نوشته شده بود. در WPF پراپرتی `TextWrapping` فقط روی
`TextBlock` و `TextBox` وجود دارد؛ `RadioButton` (و هر ContentControl دیگر) آن را ندارد.
اعتبارسنجی استاتیک v0.9.50 فقط Parse ِ XML را چک می‌کرد و خطای معنایی پراپرتی را نمی‌دید.

**اصلاح (فقط `Views/BoardPrepWindow.xaml`):** محتوای هر دو رادیوباتن به
`<RadioButton.Content><TextBlock Text="…" TextWrapping="Wrap" /></RadioButton.Content>`
منتقل شد تا رفتار wrap حفظ شود. code-behind فقط `IsChecked` را می‌خواند، پس تغییر Content
به TextBlock بی‌خطر است. شماره‌ی نسخه همان `0.9.50` ماند (روش v0.9.39a). هیچ فایل دیگری
دست نخورده است.

**سوییپ هم‌خانواده (همه PASS):** هیچ `TextWrapping` دیگری روی المنت غیر TextBlock/TextBox
در کل پروژه نیست · هر ۲۳ هندلر رویداد XAML در code-behind موجودند · همه‌ی کلیدهای
StaticResource تعریف‌شده‌اند · `x:Class` با code-behind مطابق است · سه attribute «جدید نسبت
به واژگان پروژه» (`ComboBox.DisplayMemberPath`، `TextBox.HorizontalScrollBarVisibility`،
`TextBox.IsReadOnly`) همگی پراپرتی‌های معتبر WPF هستند.

**درس ثبت‌شده:** فایل XAML **تازه** (که هرگز build واقعی ندیده) فقط با Parse ِ XML اعتبارسنجی
نمی‌شود — سوییپ «attribute به‌ازای تگ» (واژگان مجاز هر المنت) به اعتبارسنجی استاتیک تحویل
اضافه شد. در خطای `MC3072` شماره‌ی خط، انتهای بلاک المنت را نشان می‌دهد نه محل دقیق
attribute — همه‌ی attributeهای همان المنت (و المنت‌های هم‌ردیف) باید چک شوند.

## v0.9.50b — ادامه: خطای CS0246 روی ToggleButton

**رویداد:** بیلد v0.9.50a از مرحله‌ی XAML گذشت ولی CoreCompile با یک خطای C# شکست خورد:
`error CS0246: The type or namespace name 'ToggleButton' could not be found` —
`BoardPrepWindow.xaml.cs:103`: امضای `ShowPanel(FrameworkElement panel, ToggleButton tab)`
در حالی که فایل فقط `using System.Windows.Controls` دارد و `ToggleButton` در
`System.Windows.Controls.Primitives` است. implicit usings ِ WPF (System.Windows،
Controls، Input، Media…) شامل **Primitives** و **Threading** نمی‌شود. این خطا از v0.9.50
اصلی وجود داشت ولی پشت MC3072 پنهان بود (MarkupCompile قبل از CoreCompile می‌شکند).

**اصلاح (فقط یک خط):** پارامتر به `System.Windows.Controls.Primitives.ToggleButton`
fully-qualified شد — همان قاعده‌ی طلایی v0.9.39a/v0.9.41 (کامل‌نویسی نام‌های مشترک).

**سوییپ پیشگیرانه‌ی «تایپ → namespace» روی هر چهار فایل تازه‌ی C# (جلوگیری از شکست سوم):**
صفر مورد باقی‌مانده. مثبت‌کاذب‌های ردشده: `Dispatcher.BeginInvoke` (پراپرتی ارثی
DispatcherObject است — using نمی‌خواهد) · `Handshake` در BoardCheckupService (نام متد
اعلان‌شده است، نه تایپ؛ `SerialPort` همان‌جا fully qualified است) · دیالوگ‌ها
(`Microsoft.Win32.OpenFileDialog`، `System.Windows.Forms.FolderBrowserDialog`) از قبل
fully qualified · امضای هر ۲۳ هندلر XAML با نوع رویداد مطابقت دارد (Click/Checked/Unchecked
→ RoutedEventArgs · SelectionChanged کومبو → SelectionChangedEventArgs) ·
`PackageReference System.IO.Ports 8.0.0` در csproj حاضر.

**درس ثبت‌شده (تکمیل درس 50a):** فایل **C# تازه** هم مثل XAML تازه سوییپ معنایی می‌خواهد —
«هر تایپ Capitalized باید از usingهای فایل یا implicit usings بیاید». هر دو سوییپ به
چک‌های تحویل اضافه شدند.

## v0.9.50c — ادامه: ۴۷ خطای CS0103/CS0246 (using System.IO گمشده در سه سرویس)

**رویداد:** بیلد v0.9.50b از پنجره گذشت (XAML + ToggleButton ✅) ولی کامپایل با **۴۷ خطا**
متوقف شد: سه سرویس تازه (`BoardHexService` / `BoardsTxtService` / `BoardCheckupService`)
هر کدام فقط `using System.Text;` و `using System.Text.RegularExpressions;` داشتند، در حالی
که از `File` / `Path` / `Directory` / `DirectoryInfo` / `InvalidDataException` استفاده
می‌کنند.

**ریشه‌ی محیطی (تحلیل):** با اینکه csproj هر دو پروژه `ImplicitUsings=enable` دارد، روی
ماشین بیلد `System.IO` به‌صورت implicit در دسترس نبود — در حالی که namespaceهای WPF کار
می‌کردند (پنجره با همان بیلد فقط روی ToggleButton خطا داد). شواهد: هر **۸ فایل** موجود
پروژه که از File/Path استفاده می‌کنند `using System.IO;` **صریح** دارند (قرارداد واقعی
کدبیس). محتمل‌ترین علت: `<Using Remove="System.IO"/>` در یک Directory.Build.props بیرون از
زیپ (راه‌حل کلاسیک ابهام `System.IO.Path` در برابر `System.Windows.Shapes.Path`).

**اصلاح (فقط بلاک using سه فایل):**
- `BoardHexService.cs` ← `System;` `System.IO;` `System.Linq;`
- `BoardsTxtService.cs` ← `System;` `System.Collections.Generic;` `System.IO;` `System.Linq;`
- `BoardCheckupService.cs` ← `System;` `System.Collections.Generic;` `System.IO;` `System.Linq;` `System.Threading;` (برای `Thread.Sleep`)

توکن‌های مبهم چشمی تأیید شدند: `Key` در HexService = نام پارامتر record است (نه
System.Windows.Input) · `DirectoryInfo` واقعی (خط ۲۱۱ چکاپ) · `InvalidDataException` واقعی ·
`StopBits`/`Parity` فقط در کامنت · `SerialPort` از قبل fully qualified.

**درس ثبت‌شده (تکمیل 50a/50b):** فرض‌های سوییپ باید از **قرارداد کدبیسِ در حال کامپایل**
گرفته شوند، نه از مستندات SDK. چک تحویلی تازه: «هر فایل .cs که تایپ System.IO مصرف می‌کند
باید `using System.IO;` صریح داشته باشد» + سوییپ صفر-implicit روی هر فایل تازه.
