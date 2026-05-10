# Instagram Auto Liker

لوحة تحكم ذاتية الاستضافة للإعجاب التلقائي بمنشورات Instagram من حسابات مستهدفة، مع تحديد معدل الإعجابات وجدولة زمنية.

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
- Playwright + Chromium — تسجيل دخول بمتصفح حقيقي
- pyotp — توليد رموز TOTP تلقائياً
- python-jose — JWT tokens للوحة التحكم
- cryptography (Fernet) — تشفير البيانات الحساسة

---

## هيكل الملفات

```
artifacts/instagram-auto-liker/src/
├── api/client.ts              # axios instance + auth helpers + type definitions
├── pages/
│   ├── Login.tsx              # تسجيل دخول لوحة التحكم
│   ├── Dashboard.tsx          # إدارة الحسابات + TOTP/Proxy/Personality panels
│   ├── IgLogin.tsx            # ربط حساب Instagram (3 tabs + TOTP live preview)
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
│   └── settings_kv.py         # SettingsKV (key-value store)
├── schemas/
│   └── account.py             # Pydantic schemas: AccountOut, IGLoginPasswordRequest, etc.
├── routers/
│   ├── accounts.py            # CRUD + login (password/cookies/playwright) + proxy/personality/TOTP
│   ├── auth.py                # /api/auth/login (OAuth2PasswordRequestForm → JWT)
│   ├── targets.py             # CRUD الحسابات المستهدفة
│   ├── runs.py                # تشغيل يدوي / تلقائي
│   ├── logs.py                # استرجاع سجلات الإعجاب
│   ├── settings.py            # إعدادات الحدود والجدول الزمني
│   └── stats.py               # إحصاءات الاستخدام
└── services/
    ├── ig_client.py           # instagrapi wrapper + session encryption
    ├── pw_login.py            # Playwright login (real Chromium, 2FA, proxy)
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

---

## قرارات معمارية

- **Playwright على Replit/NixOS**: يستخدم Chromium من nix-store، لأن `headless-shell` المدمج مع Playwright ينقصه `libnspr4.so`. يمكن تجاوز المسار عبر `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`.
- **تشفير ثنائي المستوى**: كلمات المرور + ملفات الجلسة + مفاتيح TOTP + البروكسي — كلها مشفرة بـ Fernet قبل التخزين.
- **APScheduler داخل FastAPI**: يعمل الجدولة في نفس العملية، يبدأ عند `startup` وينتهي عند `shutdown`.
- **auth endpoint**: يستخدم `OAuth2PasswordRequestForm` → يجب إرسال البيانات كـ `application/x-www-form-urlencoded` وليس JSON.
- **Migrations تلقائية**: `init_db()` تنفذ `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` لكل column جديد — لا يوجد Alembic.

---

## Gotchas

- **مسار Python backend ثابت**: يجب تشغيله من `/home/runner/workspace/instagram-auto-liker/backend` (مضبوط في artifact.toml).
- **`MASTER_KEY` و`JWT_SECRET` ثابتان**: تغييرهما يُبطل جميع الجلسات المشفرة المخزنة.
- **`DATABASE_URL` من البيئة**: SQLite لن يُستخدم في production رغم وجوده كقيمة افتراضية في config.
- **Tailwind v4**: لا يدعم `@apply` مع class names مخصصة. استخدم CSS properties مباشرة.
- **`/api/auth/login`**: أرسل كـ `form-data` وليس JSON.
- **Playwright على VPS حقيقي** (Ubuntu/Debian): `playwright install chromium` يعمل تلقائياً بدون تعديل.
- **pyotp**: يقبل مفاتيح Base32 فقط (مثل: `JBSWY3DPEHPK3PXP`). المسافات والشرطات تُزال تلقائياً.

---

## تفضيلات المستخدم

- واجهة عربية RTL بالكامل
- لا تستخدم emojis في الكود إلا عند الطلب الصريح

---

## مؤشرات مفيدة

- راجع skill `pnpm-workspace` لهيكل monorepo وإعدادات TypeScript
