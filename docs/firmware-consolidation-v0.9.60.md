# v0.9.60 — firmware consolidation + transport hardening

این نسخه قرارداد نهایی سخت‌افزار (نسخه‌های دست‌آزمایی‌شده‌ی 0.9.59h/k/m/n) را وارد سورس و
ژنراتور `PicoFirmwareExporter` می‌کند و دو نقص انتقالی را می‌بندد.

## فرم‌ور پیکو (code.py تولیدی)

- **سنسور اختیاری:** بوت و `PING` بدون BH1750 کار می‌کنند؛ `WLUX`/`TRGLUX`/`LCAL` ← `ERR|NOSENSOR|...`
- **بافر بایتی کران‌دار** به‌جای الحاق رشته‌ای؛ نگهبان never-die دور هر خط و کل حلقه
- **پمپ دائمی بازو:** در هر تکرار حلقه و داخل `wait_range`/`LCAL`/`forward_to_arm` —
  EVTهای بازو زنده به PC می‌رسند و بافر TX بازو هرگز پر و قفل نمی‌شود
- **موس fire-and-ack:** ‏`MMOVE`/`MCLICK`/`MWHEEL`/`MDOWN`/`MUP` فوروارد + پاسخ فوری؛
  صدا و SETRES و HALT/BYE پاسخ واقعی بازو را منتظر می‌مانند
- **کیبورد همیشه Pico:** ‏`KBDPICO|` و `KBDARM|` هر دو محلی مصرف می‌شوند
- **کیپد ثابت:** GP4→GND = Num Lock = Start/Stop · GP3→GND = Scroll Lock = Pause/Resume
  (هم موتور standalone و هم کلید HID به PC)
- **امن پیش‌فرض:** `AUTOSTART = False`؛ موتور standalone تا ۳ ثانیه بعد از آخرین فرمان host ساکت است

## انتقال

- `bridge.py`: stdio اجباراً UTF-8 با errors=replace + فالبک ASCII در emit (گزارش‌گر هرگز نمی‌میرد)
- `PythonBoardBridge.cs`: ‏`StandardOutputEncoding`/`StandardErrorEncoding = Encoding.UTF8` + `PYTHONIOENCODING=utf-8`

## UI و داده

- لاگ سریال: `SelectionMode="Extended"` (کپی خطوط انتخاب‌شده واقعی شد)
- `stableSec` اعشاری: ‏0.5 → 500ms روی سیم، خلاصه‌ی «0.5s»، پارس InvariantCulture با فالبک محلی

## تست‌ها

- گام ۵۸ TestRunner: ۱۵ assertion (پین‌های نسخه، قرارداد فرم‌ور، UTF-8 هر دو طرف، multi-select، stableSec)
- گام ۴۴ به قرارداد جدید کیبورد به‌روز شد (بدون `KBD_ON_ARM`) · گام ۵۷(b) به کیپد ثابت GP4/GP3
- شبیه‌سازی سخت‌افزار ساختگی این‌طرف: ۲۳/۰ سبز
