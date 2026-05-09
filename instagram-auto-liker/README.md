# Instagram Auto Liker

> ⚠️ **تحذير قبل البدء:** هذه الأداة تنتهك [شروط استخدام Instagram](https://help.instagram.com/477434105621119). استخدامها قد يؤدي إلى:
> - تحذيرات (action blocks) أو **حظر دائم** للحساب
> - فقدان الجلسة وطلب تحقق إضافي
> - shadowban أو تقليل وصول منشوراتك
>
> **استخدمها على مسؤوليتك الشخصية وفقط لحسابك الخاص.**

تطبيق ويب شخصي يدمج بين سكريبت Python و bot يعمل في الخلفية لتسجيل الدخول إلى حساب Instagram خاص بك (عبر الكوكيز أو username/password) وتصفح آخر منشورات قائمة من الحسابات والإعجاب بها تلقائياً مع احترام rate limits لتقليل خطر الكشف.

## المكوّنات (Stack)

| الطبقة | التقنية |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Instagram Client | [instagrapi](https://github.com/subzeroid/instagrapi) (يدعم cookies + password + 2FA) |
| Scheduler | APScheduler (مهام تلقائية في الخلفية) |
| Database | SQLite + SQLAlchemy 2 |
| Encryption | Fernet (cryptography) — لتشفير الكوكيز/كلمات المرور قبل التخزين |
| Frontend | React 18 + Vite + TypeScript + Tailwind |
| Deployment | Docker Compose |

## بنية المشروع

```
instagram-auto-liker/
├── backend/          # FastAPI app + instagrapi + APScheduler
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/        # Account, Target, Run, LikeLog, SettingsKV
│   │   ├── schemas/       # Pydantic
│   │   ├── routers/       # auth, accounts, targets, runs, logs, settings
│   │   └── services/      # crypto, ig_client, liker, scheduler, auth
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/         # React dashboard
│   ├── src/
│   │   ├── pages/         # Login, Dashboard, IgLogin, Targets, Schedule, Logs
│   │   ├── components/    # Layout
│   │   └── api/client.ts
│   ├── package.json
│   └── Dockerfile
├── scripts/
│   └── generate_keys.py   # توليد مفاتيح آمنة لـ .env
├── docker-compose.yml
├── .env.example
└── README.md
```

## التشغيل المحلي (Docker — الأسهل)

### 1) إعداد `.env`

```bash
cp .env.example .env
python3 scripts/generate_keys.py >> .env   # يطبع مفاتيح عشوائية قوية
# عدّل ADMIN_USERNAME و ADMIN_PASSWORD يدوياً ليناسبك
```

> **مهم:** احتفظ بنسخة احتياطية من `MASTER_KEY` — إذا فقدته لن تستطيع فك تشفير جلسات Instagram المخزّنة.

### 2) بدء التشغيل

```bash
docker-compose up -d --build
```

- الواجهة: http://localhost:3000
- API + توثيق Swagger: http://localhost:8000/docs

### 3) الاستخدام

1. سجّل دخول لوحة التحكم بـ `ADMIN_USERNAME` / `ADMIN_PASSWORD`.
2. اذهب لصفحة **"تسجيل دخول Instagram"** وأضف حسابك (بكلمة السر أو بالكوكيز).
3. اذهب إلى **"الحسابات المستهدفة"** للحساب وأضف usernames تريد الإعجاب بآخر منشوراتها.
4. اذهب إلى **"الجدولة والحدود"** لتفعيل التشغيل التلقائي وضبط:
   - الفاصل الزمني (مثلاً كل 6 ساعات)
   - الحد اليومي للإعجابات (يُنصح ≤ 100)
   - الحد بالساعة (يُنصح ≤ 20)
   - التأخير العشوائي بين الإعجابات (30–90 ثانية)
5. أو اضغط **"تشغيل الآن"** لبدء جولة فورية.

## التشغيل بدون Docker (للتطوير)

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

## استخراج الكوكيز من المتصفح

### Chrome/Edge (الأسهل)

1. ثبّت إضافة [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
2. افتح instagram.com وسجّل دخول عادي
3. افتح Cookie-Editor → **Export** → اختر **JSON**
4. الصق المحتوى في حقل "كوكيز / ملف الجلسة" بالواجهة

### عبر `instagrapi` مباشرة

```python
from instagrapi import Client
cl = Client()
cl.login("username", "password")
# انسخ كامل الـ JSON الناتج إلى الواجهة
print(cl.get_settings())
```

## النشر السحابي (VPS)

```bash
# على VPS (Ubuntu) مع Docker
git clone <your-repo-or-tar> instagram-auto-liker
cd instagram-auto-liker
cp .env.example .env
python3 scripts/generate_keys.py >> .env
nano .env   # عدّل ADMIN_USERNAME/ADMIN_PASSWORD
docker-compose up -d --build

# (اختياري) ضع Caddy/Nginx أمامه مع HTTPS
```

> **مهم:** لا تكشف الواجهة على الإنترنت بدون HTTPS — كلمات المرور والجلسات حساسة.

## نصائح لتقليل خطر الحظر

- ابدأ بحدود **منخفضة جداً** (10 إعجاب/يوم) في الأسبوع الأول، ثم زدها تدريجياً.
- لا تشغّل عدة بوتس متوازية على نفس الحساب.
- استخدم نفس الـ IP الذي تسجّل دخول منه عادة (تجنّب IPs مشكوك فيها).
- إذا ظهر `feedback_required` أو `challenge_required` — **توقف فوراً ليوم على الأقل**.
- يفضّل تسجيل الدخول بالكوكيز (من جلسة متصفحك العادية) بدلاً من الباسورد.

## التطوير والاختبار

```bash
# Backend
cd backend
ruff check app
mypy app
pytest

# Frontend
cd frontend
npm run lint
npm run typecheck
npm run build
```

## الترخيص

MIT — راجع [LICENSE](./LICENSE).

## إخلاء المسؤولية

هذا المشروع للأغراض التعليمية والاستخدام الشخصي. المؤلفون **غير مسؤولين** عن أي ضرر أو حظر يلحق بحساباتك. أنت تتحمّل كامل المسؤولية عن استخدام هذه الأداة.
