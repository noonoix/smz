# v0.9.55 - بیست صفحه‌کلید بدون ماکرو، تنظیمات درون‌پنجره‌ای، سر مجموعه‌های قابل نام‌گذاری

## 1) بیست هویت صفحه‌کلید

هر بیست مورد لیست کاربر به `BoardHexService.DeviceModes` و به جدول شناسایی چکاپ
(`BoardCheckupService.KnownIdentities`) اضافه شد؛ برای هر کدام یک ردیف بوت‌لودر و یک ردیف
اپلیکیشن (PID اپ = PID بوت + ۱). همه کلاس `0x02` (CDC) ماندند تا پورت سریال و آپلود نیفتد.

| دستگاه | VID:PID بوت | نام محصول | سازنده |
|---|---|---|---|
| Logitech G413 TKL SE | 046D:C33A | G413 TKL SE Gaming Keyboard | Logitech |
| Logitech G413 SE | 046D:C33C | G413 SE Gaming Keyboard | Logitech |
| Logitech G PRO X TKL Rapid | 046D:C35E | PRO X TKL RAPID | Logitech |
| Razer BlackWidow TE | 1532:011C | BlackWidow Tournament Ed. | Razer |
| Razer BlackWidow X TE | 1532:021B | BlackWidow X Tournament Ed | Razer |
| ZOWIE Celeritas II | 1AF3:0025 | CELERITAS II | ZOWIE |
| CHERRY XTRFY MX 8.3 TKL | 046A:00B1 | XTRFY MX 8.3 TKL | CHERRY |
| HyperX Alloy Origins | 0951:16E5 | HyperX Alloy Origins | HyperX |
| HyperX Alloy Origins 60 | 0951:16E9 | HyperX Alloy Origins 60 | HyperX |
| HyperX Alloy Origins 65 | 0951:16EB | HyperX Alloy Origins 65 | HyperX |
| Ducky One 2 Mini | 04D9:0348 | Ducky One 2 Mini | DuckyChannel |
| Ducky One 2 Pro Mini | 04D9:0356 | Ducky One 2 Pro Mini | DuckyChannel |
| SteelSeries Apex Pro TKL | 1038:1614 | Apex Pro TKL | SteelSeries |
| SteelSeries Apex Pro Mini | 1038:1646 | Apex Pro Mini | SteelSeries |
| Keychron K8 | 3434:0180 | Keychron K8 | Keychron |
| Das Keyboard 5QS Mark II | 24F0:2038 | Das Keyboard 5QS Mark II | Metadot |
| Zalman ZM-K650-WP | 258A:0006 | ZM-K650-WP | Zalman |
| Corsair Vanguard Pro 96 | 1B1C:1BC4 | VANGUARD PRO 96 | Corsair |
| Fantech Shikari K515 | 0C45:7A0C | Shikari K515 | Fantech |
| GAMEON KENORA GOMK87-RS | 258A:010C | KENORA GOMK87-RS | GAMEON |

**نکته‌ی مهم درباره‌ی دقت داده‌ها:** VID هر برند از پایگاه رسمی USB-ID گرفته شده و قطعی است
(Logitech 046D، Razer 1532، Ducky/Holtek 04D9، SteelSeries 1038، Keychron 3434، Metadot 24F0،
Corsair 1B1C، HyperX/Kingston 0951، CHERRY 046A، ZOWIE/Kingsis 1AF3، SINO WEALTH 258A، SONiX 0C45).
بخشی از PIDها در پایگاه‌های عمومی برای همان خانواده ثبت شده و بخشی تخمین خانوادگی است؛ چون این
مقادیر فقط «پیش‌فرض قابل ویرایش» هستند، اگر PID واقعی دستگاهتان را در چکاپ دیدید می‌توانید در
همان فرم مشخصات برد اصلاحش کنید.

## 2) نوار اسکرول از متن فاصله گرفت

همه‌ی پنل‌های اسکرول‌دار (دیالوگ استپ، جست‌وجوی تصویر، سه تب آماده‌سازی برد و پنل تنظیمات)
حالا `Padding="14,0,14,0"` دارند، پس نوار اسکرول دیگر روی متن فارسی نمی‌نشیند.

## 3) تودِ‌تیپ و زیرمنو دیگر روی هم نمی‌افتند

راهنمای شناور دکمه‌های ریل به زیر آیکون منتقل شد (`Placement=Bottom`, offset ۸px) و تا وقتی
زیرمنوی همان آیکون باز است کاملاً خاموش می‌شود (`ToolTipService.SetIsEnabled`).

## 4) تنظیمات، پنجره‌ی جدا نیست

`OptionsDialog` حالا محتوایش را جدا می‌کند (`EmbedContent`) و `MainWindow` آن را در یک پنل
راست‌چسبیده‌ی درون همان پنجره نشان می‌دهد (`SettingsOverlay` + `SettingsHost`).
هر چهار بخش (سریال، اجرا، کلیدهای میان‌بر، نقش‌ها) دست‌نخورده و کامل‌اند؛ تأیید/انصراف از طریق
رویداد `Completed` کار می‌کند (جای `DialogResult` که فقط برای پنجره‌ی واقعی معنی داشت).

## 5) نام‌گذاری سر مجموعه‌ها با نگه‌داشتن نماد

هر شش بلوک ظرف (For Loop، Parallel Group، Random Package، Wait For Sound، Wait For Light،
Find Image) فیلد جدید «عنوان مجموعه» دارند. با پر کردنش، سر مجموعه به شکل
`نماد + عنوان دلخواه + دنباله‌ی اطلاعاتی` نشان داده می‌شود؛ نمادها: 🔁 حلقه · ⚡ همزمان ·
🎲 تصادفی · 🔊 صدا · 💡 نور · 🔍 تصویر. خالی گذاشتن = همان نام پیش‌فرض قبلی.

## 6) نشانگرهای `next` و `else`

نشانگرهای ساختاری بدون `#` و با حرف کوچک نوشته می‌شوند (`next`، `else`، `end if`) و چون
ستون دکمه‌ی آکاردئون را ندارند، برچسبشان ۱۲ پیکسل به چپ کشیده شد تا به رگ قرمز بچسبد.
یادداشت‌های واقعی همچنان با `# ` نمایش داده می‌شوند.
