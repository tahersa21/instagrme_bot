# Changelog — Instagram Auto Liker

جميع التغييرات والإصلاحات الموثقة لهذا المشروع.

---

## [0.6.0] — إصلاح Playwright على Replit (مكتبات النظام)

### مُصلح
- **خطأ `libnspr4.so: No such file or directory`**: كانت Chrome for Testing تفشل عند التشغيل لأن ~25 مكتبة نظام (glib، nspr، nss، atk، cups، dbus، xkbcommon، alsa، gbm، X11، cairo، pango...) غائبة.
- **الحل**: تثبيت جميع المكتبات المطلوبة عبر Nix (`installSystemDependencies`) بدلاً من `apt-get` المحجوب في Replit.
- **`_chromium_can_run()`** دالة جديدة تتحقق بـ `ldd` أن جميع shared libs محلولة — لا مجرد وجود الملف.
- **`ensure_chromium_installed()`** محسّنة: تُجرب `install-deps` أولاً (تعمل على Ubuntu حقيقي)، ثم تتراجع gracefully، ثم تُعيد تنزيل الـ browser فقط إذا أثبت `ldd` وجود مكتبات ناقصة.

### مُصلح (سابق — v0.5)
- **خطأ `ETXTBSY`**: race condition بين تثبيت Chromium في الخلفية وطلب login وارد في نفس الوقت.
- **الحل**: تشغيل `ensure_chromium_installed()` بشكل متزامن قبل قبول أي طلب.

---

## [0.5.0] — إعادة تنشيط الحسابات الموقوفة

### مضاف
- **`PATCH /api/accounts/{id}/reactivate`** — endpoint جديد يُعيد تنشيط حساب موقوف:
  - يستدعي `ig_client.relogin_account()` باستخدام كلمة المرور المخزنة + TOTP
  - يُحدِّث `is_active=True` عند النجاح
  - يُرسل HTTP 400 مع رسالة عربية واضحة عند الفشل
  - محمي بـ `get_current_user`

- **زر "إعادة التنشيط"** في Dashboard.tsx:
  - يظهر فقط عندما `is_active === false`
  - يُظهر نص "جارٍ التنشيط..." أثناء الطلب
  - رسالة خطأ حمراء منفصلة عن `last_error`

---

## [0.4.0] — 2FA TOTP تلقائي

### مضاف
- **`services/totp.py`** — خدمة TOTP جديدة تعتمد على `pyotp`:
  - `generate_code(secret)` — توليد رمز 6 أرقام من مفتاح Base32
  - `validate_secret(secret)` — التحقق من صحة المفتاح وتنظيفه
  - `time_remaining()` — ثواني المتبقية حتى تجديد الرمز (0-29)
  - يرفع `TOTPError` برسائل خطأ عربية واضحة

- **`models/account.py`** — عمود `encrypted_totp_secret TEXT` للحساب

- **`database.py`** — migration تلقائي `ALTER TABLE accounts ADD COLUMN IF NOT EXISTS encrypted_totp_secret TEXT`

- **`schemas/account.py`**:
  - `TOTPUpdateRequest` — schema لحفظ/حذف مفتاح TOTP
  - `has_totp: bool` في `AccountOut`
  - `totp_secret: str | None` في `IGLoginPasswordRequest` و `IGLoginPlaywrightRequest`

- **`routers/accounts.py`**:
  - `POST /api/accounts/totp/preview` — معاينة رمز TOTP حي بدون حفظ
  - `PATCH /api/accounts/{id}/totp` — حفظ أو حذف مفتاح TOTP لحساب موجود
  - `_resolve_verification_code()` — يولّد الرمز تلقائياً من TOTP secret عوضاً عن إدخال يدوي
  - جميع login endpoints تقبل `totp_secret` وتخزنه مشفراً

- **`pages/IgLogin.tsx`** — قسم 2FA قابل للطي مع:
  - حقل إدخال مفتاح TOTP
  - عرض الرمز الحي يتجدد كل 30 ثانية
  - شريط مؤقت بالألوان (🟢 أخضر / 🟡 أصفر / 🔴 أحمر)

- **`pages/Dashboard.tsx`** — لوحة TOTP لكل حساب:
  - زر `🔐 2FA` يفتح/يغلق اللوحة
  - بادج `🔐 2FA تلقائي` على الحسابات المفعّلة
  - عرض رمز TOTP حي مع عداد تنازلي داخل Dashboard
  - حفظ أو حذف المفتاح في أي وقت

### مُصلح
- `routers/accounts.py`: إضافة `from pydantic import BaseModel` (كانت تسبب `NameError` عند التشغيل)

---

## [0.3.0] — تسجيل الدخول بـ Playwright

### مضاف
- **`services/pw_login.py`** — تسجيل دخول كامل بمتصفح Chromium حقيقي:
  - كتابة بشرية مع تأخيرات عشوائية
  - دعم 2FA code injection (يدوي أو TOTP تلقائي)
  - استخراج cookies وتسليمها لـ instagrapi
  - دعم HTTP/SOCKS proxy لكل حساب
  - `PW2FARequired`, `PWChallengeRequired`, `PWLoginError` exceptions

- **`POST /api/accounts/login/playwright`** — endpoint جديد

- **`pages/IgLogin.tsx`** — tab ثالث "Playwright" مع توضيح المميزات

### مُصلح
- **`pw_login.py` — زر Confirm للـ 2FA**: استبدال selector ثابت بقائمة fallback selectors:
  ```
  button:has-text("Confirm") → button:has-text("Verify") → button[type="submit"] → Enter
  ```
  يجرب كل selector بالترتيب ويضغط Enter إذا فشل الكل.

- **Chromium على Replit/NixOS**: استخدام `/nix/store/.../chrome` من nix-store لأن `headless-shell` المدمج ينقصه `libnspr4.so`. يمكن تجاوزه بـ `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`.

---

## [0.2.0] — Anti-Detection + شخصية الحساب + البروكسي

### مضاف
- **شخصية لكل حساب** (`personality` JSON):
  - `skip_rate` — نسبة المنشورات المتخطاة عشوائياً (5%-35%)
  - `session_style` — `active` / `moderate` / `quiet`
  - `warmup_count` — عدد حركات الإحماء قبل البدء

- **بروكسي مخصص لكل حساب**:
  - دعم `http://`, `https://`, `socks5://`, `socks4://`
  - أنواع: `residential` / `mobile_4g` / `datacenter`
  - مشفر بـ Fernet قبل التخزين

- **`PATCH /api/accounts/{id}/proxy`** — تحديث البروكسي
- **`PATCH /api/accounts/{id}/personality`** — تحديث الشخصية

- **`pages/Dashboard.tsx`** — لوحات Proxy و Personality لكل حساب
- **`pages/Analytics.tsx`** — صفحة تحليلات وإحصاءات

### مُصلح
- تدفق CSS الـ RTL في layout الأزرار والـ toggles
- أنماط Tailwind v4: استبدال `@apply` بـ CSS properties مباشرة

---

## [0.1.0] — الإصدار الأولي

### مضاف
- **Backend FastAPI كامل**:
  - Auth بـ JWT (OAuth2PasswordRequestForm)
  - CRUD الحسابات، الأهداف، الجلسات، الإعدادات
  - APScheduler للتشغيل الدوري
  - instagrapi للتفاعل مع Instagram API
  - Fernet encryption لجميع البيانات الحساسة
  - Migrations تلقائية بدون Alembic

- **Frontend React/Vite**:
  - صفحات: Login, Dashboard, IgLogin, Targets, Schedule, Logs
  - واجهة عربية RTL كاملة
  - TanStack Query للبيانات + Axios

- **PostgreSQL**: قاعدة بيانات مع models: Account, Target, Run, LikeLog, SettingsKV

- **تسجيل دخول Instagram**:
  - بكلمة المرور (instagrapi مباشرة)
  - بـ Cookies (session import)

---

## إصلاحات عبر الإصدارات

| المشكلة | الحل |
|---------|------|
| `NameError: BaseModel` في accounts.py | إضافة `from pydantic import BaseModel` |
| `libnspr4.so` مفقود في Playwright | استخدام Chromium من nix-store |
| زر Confirm للـ 2FA لا يعمل دائماً | قائمة fallback selectors + Enter |
| `@apply` لا يعمل في Tailwind v4 | CSS properties مباشرة |
| `AUTH` endpoint يفشل بـ JSON | تغيير إلى `form-data` |
| Overflow في RTL layout | إصلاح CSS flex direction |
