# smc — Classroom Studio CI

هر push به `main` به‌طور خودکار روی رانر ویندوزی رایگان GitHub:

1. `bridge.py` را py_compile می‌کند (درس v0.9.58)
2. بیلد Release می‌گیرد
3. TestRunner را اجرا می‌کند — **اگر حتی یک تست قرمز باشد، زیپ ساخته نمی‌شود**
4. سبز → یک Release با `Classroom-Studio-release.zip` + `test-output.txt` + `sha256.txt`
5. قرمز → یک Issue با دمِ لاگ تست باز می‌شود

این قراردادهای CI پس از انتقال پروژه به مخزن جدید نیز حفظ شده‌اند.
