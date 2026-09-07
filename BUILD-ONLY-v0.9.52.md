# BUILD-ONLY — v0.9.52

**Rule 8 still applies: build and test only. Do not redesign, refactor or "improve" anything.**

## چه چیزی عوض شد

1. `Services/HotPlugWatcher.cs` — **فایل جدید** (منطق تشخیص اتصال گرم).
2. `ViewModels/MainViewModel.cs` — `StartPortWatcher` / `OnPortWatcherTick` / `SyncPortChoices` + بنر نسخه.
3. `Views/BoardPrepWindow.xaml` + `.xaml.cs` — ویزارد چهار قدمی، آیکون برداری، نوار قدم، RTL، کارت مشخصات در قدم ۱.
4. `Services/BoardHexService.cs` + `Services/BoardCheckupService.cs` — شش دستگاه آموزشی.
5. `tests/TestRunner.cs` — گام ۵۲ (۱۸ ادعا) + پین‌های نسخه.
6. `Ams.UI.csproj` / `PicoFirmwareExporter.cs` — نسخه 0.9.52.

## کاری که باید انجام شود

```
dotnet build ams-shell/src/Ams.UI/Ams.UI.csproj -c Release
dotnet run --project tests > test-output-v0.9.52.txt
```

## پذیرش

- ۰ error در بیلد برنامه **و** در پروژه‌ی تست.
- در خروجی تست: `0 failed` و هر ۱۸ خط `v0.9.52:` با PASS.
- `FileVersion = 0.9.52.0`.
- اگر خطایی دیدید: **فقط** متن خطا (کد، فایل، خط، ستون) را در `build-v0.9.52.txt` برگردانید؛ خودتان اصلاح نکنید.
