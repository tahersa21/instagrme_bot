# Instagram Auto Liker

لوحة تحكم ذاتية الاستضافة للإعجاب التلقائي بمنشورات Instagram من حسابات مستهدفة، مع تحديد معدل الإعجابات وجدولة زمنية، **وميزة إنشاء حسابات Instagram تلقائياً** عبر Mailgun + مزوّدي SMS.

---

## تشغيل المشروع

| الخدمة | الأمر | الرابط |
|--------|-------|--------|
| **Frontend** | `artifacts/instagram-auto-liker: web` | `/` (port 18962) |
| **Backend** | `artifacts/api-server: API Server` | `/api` (port 8080) |

بيانات دخول لوحة التحكم: **admin / admin123**
قابلة للتغيير عبر متغيري البيئة `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

---

## Stack التقني

### Frontend
- React 19 + Vite 7 + TypeScript 5.9
- Tailwind CSS v4 (بدون `@apply` على class names مخصصة)
- React Router v6 + TanStack Query + Axios
- واجهة عربية RTL بالكامل

### Backend
- Python 3.11 + FastAPI + uvicorn (--reload)
- SQLAlchemy 2 + PostgreSQL (psycopg2-binary)
- APScheduler (داخل FastAPI process)
- instagrapi — Private Instagram API client
- Playwright + Chromium — تسجيل دخول وإنشاء حسابات بمتصفح حقيقي
- pyotp — توليد رموز TOTP تلقائياً
- python-jose — JWT tokens للوحة التحكم
- cryptography (Fernet) — تشفير البيانات الحساسة
- httpx — استدعاءات Mailgun و sms-activate و 5sim

---

## هيكل الملفات

```
artifacts/instagram-auto-liker/src/
├── api/client.ts              # axios instance + auth helpers + type definitions
├── pages/
│   ├── Login.tsx              # تسجيل دخول لوحة التحكم
│   ├── Dashboard.tsx          # إدارة الحسابات + TOTP/Proxy/Personality panels
│   ├── IgLogin.tsx            # ربط حساب Instagram (3 tabs + TOTP live preview)
│   ├── CreateAccount.tsx      # إنشاء حساب Instagram تلقائياً + عارض المهام
│   ├── Domains.tsx            # إدارة نطاقات Mailgun
│   ├── SmsProviders.tsx       # إدارة مزوّدي SMS (5sim / sms-activate)
│   ├── Targets.tsx            # إدارة الحسابات المستهدفة
│   ├── Schedule.tsx           # ضبط الجدول الزمني والحدود
│   ├── Logs.tsx               # سجل عمليات الإعجاب
│   └── Analytics.tsx          # إحصاءات وتحليلات
└── components/Layout.tsx      # sidebar + nav

instagram-auto-liker/backend/app/
├── main.py                    # app factory, CORS, router registration, lifespan
├── config.py                  # Settings (pydantic-settings, env vars)
├── database.py                # SQLAlchemy engine + init_db() + migrations
├── models/
│   ├── account.py             # Account ORM model
│   ├── target.py              # Target ORM model
│   ├── run.py                 # Run ORM model
│   ├── like_log.py            # LikeLog ORM model
│   ├── settings_kv.py         # SettingsKV (key-value store)
│   ├── domain.py              # Domain (Mailgun)
│   ├── sms_provider.py        # SmsProvider (5sim / sms-activate)
│   └── account_creation_job.py # AccountCreationJob lifecycle
├── schemas/
│   ├── account.py             # Pydantic schemas: AccountOut, IGLoginPasswordRequest, etc.
│   ├── domain.py              # DomainCreate/Update/Out
│   ├── sms_provider.py        # SmsProviderCreate/Update/Out
│   └── account_creation.py    # AccountCreateRequest, AccountCreationJobOut
├── routers/
│   ├── accounts.py            # CRUD + login (password/cookies/playwright) + proxy/personality/TOTP
│   ├── auth.py                # /api/auth/login (OAuth2PasswordRequestForm → JWT)
│   ├── targets.py             # CRUD الحسابات المستهدفة
│   ├── runs.py                # تشغيل يدوي / تلقائي
│   ├── logs.py                # استرجاع سجلات الإعجاب
│   ├── settings.py            # إعدادات الحدود والجدول الزمني
│   ├── stats.py               # إحصاءات الاستخدام
│   ├── domains.py             # CRUD نطاقات Mailgun
│   ├── sms_providers.py       # CRUD مزوّدي SMS
│   └── account_creation.py    # تشغيل + متابعة مهام إنشاء الحسابات
└── services/
    ├── ig_client.py           # instagrapi wrapper + session encryption
    ├── pw_login.py            # Playwright login (real Chromium, 2FA, proxy)
    ├── ig_signup.py           # Playwright signup flow (email/phone OTP)
    ├── mailgun.py             # Mailgun Events API → extract email OTP
    ├── sms_provider.py        # 5sim + sms-activate API wrappers
    ├── account_creator.py     # تنسيق مهمة الإنشاء في BackgroundTasks thread
    ├── totp.py                # TOTP utilities (pyotp): generate_code, validate_secret, time_remaining
    ├── liker.py               # منطق الإعجاب + anti-detection delays
    ├── scheduler.py           # APScheduler wrapper
    ├── crypto.py              # Fernet encrypt/decrypt
    └── auth.py                # JWT helpers + get_current_user dependency
```

---

## متغيرات البيئة المطلوبة

| المتغير | الوصف | مثال |
|---------|-------|------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `MASTER_KEY` | Fernet key لتشفير الجلسات والكلمات المرور | توليد: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `JWT_SECRET` | Secret لتوقيع JWT tokens | أي string عشوائي طويل |
| `ADMIN_USERNAME` | اسم مستخدم لوحة التحكم | `admin` |
| `ADMIN_PASSWORD` | كلمة مرور لوحة التحكم | `admin123` |
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` | (اختياري) مسار Chromium مخصص | انظر Gotchas |

> ملاحظة: مفاتيح Mailgun ومزوّدي SMS تُدخل من واجهة لوحة التحكم وتُشفَّر بـ Fernet داخل قاعدة البيانات — لا حاجة لمتغيرات بيئة لها.

---

## API Endpoints الرئيسية

### Auth
| Method | Path | الوصف |
|--------|------|-------|
| POST | `/api/auth/login` | تسجيل دخول لوحة التحكم → JWT token |

### Accounts
| Method | Path | الوصف |
|--------|------|-------|
| GET | `/api/accounts` | قائمة الحسابات |
| POST | `/api/accounts/login/password` | ربط حساب بكلمة المرور |
| POST | `/api/accounts/login/cookies` | ربط حساب بـ Cookies |
| POST | `/api/accounts/login/playwright` | ربط حساب بمتصفح Chromium حقيقي |
| POST | `/api/accounts/totp/preview` | معاينة رمز TOTP حي |
| PATCH | `/api/accounts/{id}/totp` | حفظ / حذف مفتاح TOTP |
| PATCH | `/api/accounts/{id}/proxy` | تحديث البروكسي |
| PATCH | `/api/accounts/{id}/personality` | تحديث ملف الشخصية |
| DELETE | `/api/accounts/{id}` | حذف الحساب |

### Domains (Mailgun)
| Method | Path | الوصف |
|--------|------|-------|
| GET | `/api/domains` | قائمة النطاقات |
| POST | `/api/domains` | إضافة نطاق + Mailgun API key |
| PATCH | `/api/domains/{id}` | تعديل النطاق / المفتاح / الافتراضي |
| DELETE | `/api/domains/{id}` | حذف (409 إن كان مرتبطاً بمهام) |

### SMS Providers
| Method | Path | الوصف |
|--------|------|-------|
| GET | `/api/sms-providers` | قائمة المزوّدين |
| POST | `/api/sms-providers` | إضافة مزوّد (5sim / sms-activate) |
| PATCH | `/api/sms-providers/{id}` | تعديل |
| DELETE | `/api/sms-providers/{id}` | حذف (409 إن كان مرتبطاً بمهام) |

### Account Creation
| Method | Path | الوصف |
|--------|------|-------|
| GET | `/api/account-creation` | قائمة آخر 100 مهمة |
| POST | `/api/account-creation` | بدء مهمة إنشاء حساب جديد |
| GET | `/api/account-creation/{id}` | تفاصيل + سجل الأحداث |
| DELETE | `/api/account-creation/{id}` | حذف من السجل |

---

## تدفق إنشاء الحساب التلقائي

1. المستخدم يضيف نطاق Mailgun (مع API key) من صفحة "النطاقات".
2. (اختياري) يضيف مفتاح 5sim أو sms-activate من صفحة "مزوّدو SMS".
3. من صفحة "إنشاء حساب تلقائي" يختار النطاق والمزوّد ويضغط "ابدأ".
4. الخادم ينشئ صف `AccountCreationJob`، يولّد بريداً عشوائياً على النطاق، ويُشغّل المهمة في خيط خلفي.
5. الخيط يفتح Chromium بـ Playwright (مع البروكسي إن وُجد)، يملأ النموذج، ويتحرّك إلى شاشة OTP.
6. خدمة `mailgun.py` تستعلم Mailgun Events API كل 5 ثوانٍ حتى يصل البريد، تستخرج رقماً من 6 خانات وتُدخله.
7. إن طلب Instagram تحقّقاً هاتفياً، يطلب الخادم رقماً من المزوّد، يُدخله في النموذج، ثم يستلم رمز SMS من نفس المزوّد ويُدخله.
8. عند النجاح، يُحفظ صف `Account` جديد بـ session cookies مشفّرة، وتظهر الحالة `success` في الواجهة.

---

## قرارات معمارية

- **Playwright على Replit**: البيئة Ubuntu 24.04 وليس NixOS. Chrome for Testing يحتاج ~25 مكتبة نظام (glib، nspr، nss، atk، cups...) تُثبَّت عبر Nix (`installSystemDependencies`). `apt-get` محجوب في Replit. `ensure_chromium_installed()` تُشغَّل في **background thread** (`run_in_executor`) عند startup حتى يبدأ uvicorn فوراً ويجتاز فحص الصحة — ثم تكتمل عملية التثبيت في الخلفية.
- **health check path**: يجب أن يكون `/api/health` (GET → 200) في `artifact.toml`.
- **تشفير ثنائي المستوى**: كلمات المرور + ملفات الجلسة + مفاتيح TOTP + البروكسي + مفاتيح Mailgun + مفاتيح SMS — كلها مشفرة بـ Fernet قبل التخزين.
- **APScheduler داخل FastAPI**: يعمل الجدولة في نفس العملية، يبدأ عند `startup` وينتهي عند `shutdown`.
- **auth endpoint**: يستخدم `OAuth2PasswordRequestForm` → يجب إرسال البيانات كـ `application/x-www-form-urlencoded` وليس JSON.
- **Migrations تلقائية**: `init_db()` تنفذ `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` للأعمدة الجديدة، والجداول الجديدة تُنشأ بـ `create_all()` — لا يوجد Alembic.
- **مهام الإنشاء الخلفية**: تُشغَّل عبر `BackgroundTasks` بجلسة `SessionLocal` مستقلة لتجنّب مشاركة الجلسة بين الخيوط.

---

## Gotchas

- **مسار Python backend ثابت**: يجب تشغيله من `/home/runner/workspace/instagram-auto-liker/backend` (مضبوط في artifact.toml).
- **`MASTER_KEY` و`JWT_SECRET` ثابتان**: تغييرهما يُبطل جميع الجلسات والمفاتيح المشفرة المخزنة.
- **`DATABASE_URL` من البيئة**: SQLite لن يُستخدم في production رغم وجوده كقيمة افتراضية في config.
- **Tailwind v4**: لا يدعم `@apply` مع class names مخصصة. استخدم CSS properties مباشرة.
- **`/api/auth/login`**: أرسل كـ `form-data` وليس JSON.
- **Playwright على VPS حقيقي** (Ubuntu/Debian): `playwright install chromium` يعمل تلقائياً بدون تعديل.
- **pyotp**: يقبل مفاتيح Base32 فقط (مثل: `JBSWY3DPEHPK3PXP`). المسافات والشرطات تُزال تلقائياً.
- **إنشاء الحسابات يخالف TOS**: نسبة النجاح أقل من 30%. Instagram يرفض IP غير الموثوقة بسرعة — يُنصح بشدة باستخدام بروكسي **residential** ونطاق Mailgun مع DKIM/SPF صحيحَين.
- **Mailgun Inbound Routing**: يجب تكوين route على Mailgun من نوع "Forward" أو "Store and notify" نحو `match_recipient(".*@yourdomain.com")` حتى تُخزَّن الرسائل وتظهر في Events API.
- **رمز دولة 5sim**: استخدم اسم الدولة (مثل `russia` أو `any`)، وليس رقماً. أمّا sms-activate فيستخدم أرقاماً (0 = أي).

---

## تفضيلات المستخدم

- واجهة عربية RTL بالكامل
- لا تستخدم emojis في الكود إلا عند الطلب الصريح

---

## مؤشرات مفيدة

- راجع skill `pnpm-workspace` لهيكل monorepo وإعدادات TypeScript
