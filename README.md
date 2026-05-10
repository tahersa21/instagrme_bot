# Instagram Auto Liker 🤖

لوحة تحكم ذاتية الاستضافة للإعجاب التلقائي بمنشورات Instagram من حسابات مستهدفة.  
Self-hosted dashboard for automatically liking Instagram posts from target accounts.

---

## المميزات | Features

- **إدارة متعددة الحسابات** — ربط أي عدد من حسابات Instagram
- **3 طرق تسجيل دخول**: كلمة المرور / Cookies / متصفح Chromium حقيقي (Playwright)
- **2FA تلقائي** — حفظ مفتاح TOTP مشفر وتوليد الرمز تلقائياً عند كل دخول
- **بروكسي مخصص** — HTTP/HTTPS/SOCKS5 لكل حساب على حدة
- **شخصية لكل حساب** — معدل التخطي / أسلوب الجلسة / حركات الإحماء
- **جدولة تلقائية** — تشغيل كل عدة ساعات قابل للضبط
- **حدود الأمان** — حد يومي + حد كل ساعة + تأخيرات عشوائية
- **سجل كامل** — تتبع كل إعجاب مع التوقيت والحالة
- **تحليلات** — إحصاءات الأداء عبر الزمن
- **واجهة عربية RTL** — كاملة ومتجاوبة

---

## المتطلبات | Requirements

- Python 3.11+
- Node.js 20+ / pnpm 9+
- PostgreSQL (أو Replit Database)
- Playwright Chromium (للدخول بالمتصفح)

---

## التثبيت | Installation

### 1. نسخ المستودع
```bash
git clone https://github.com/tahersa21/instagrme_bot.git
cd instagrme_bot
```

### 2. إعداد متغيرات البيئة
أنشئ ملف `.env` في `instagram-auto-liker/backend/`:
```env
DATABASE_URL=postgresql://user:password@localhost/instagram_liker
MASTER_KEY=<Fernet key>
JWT_SECRET=<random secret>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password
```

لتوليد `MASTER_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. تثبيت Backend
```bash
cd instagram-auto-liker/backend
pip install -e .
playwright install chromium
```

### 4. تثبيت Frontend
```bash
pnpm install
```

### 5. تشغيل المشروع
```bash
# Backend
cd instagram-auto-liker/backend
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Frontend (في terminal آخر)
pnpm --filter @workspace/instagram-auto-liker run dev
```

افتح المتصفح على `http://localhost:5173` وسجّل الدخول بـ `admin / your-password`.

---

## الاستخدام | Usage

### 1. ربط حساب Instagram
انتقل إلى **"ربط حساب"** واختر طريقة الدخول:
- **كلمة المرور**: الأسرع، قد يُفعّل تحدي أمني
- **Cookies**: الأكثر أماناً، تحتاج استخراج cookies من متصفحك
- **Playwright** (موصى به): يستخدم متصفح Chromium حقيقي

إذا كان حسابك يستخدم 2FA:
1. اذهب إلى إعدادات Instagram → الأمان → التحقق بخطوتين → تطبيق المصادقة → "لا أستطيع مسح الرمز"
2. انسخ المفتاح السري (Base32)
3. الصقه في حقل **"مفتاح TOTP"** — سيُعرض الرمز الحي مباشرة

### 2. إضافة حسابات مستهدفة
انتقل إلى **"الحسابات المستهدفة"** وأضف usernames الحسابات التي تريد الإعجاب بمنشوراتها.

### 3. ضبط الإعدادات
انتقل إلى **"الجدول الزمني"** وضبط:
- عدد الإعجابات لكل حساب في كل تشغيل
- الحد اليومي والحد كل ساعة
- الفترة الزمنية بين التشغيلات التلقائية
- التأخير بين كل إعجاب (min/max ثانية)

### 4. التشغيل
- **يدوي**: اضغط زر ▶ بجانب الحساب في Dashboard
- **تلقائي**: يعمل في الخلفية حسب الجدول المضبوط

---

## البنية التقنية | Architecture

```
┌─────────────────┐        ┌──────────────────────────────┐
│  React Frontend  │ ←───→ │     FastAPI Backend           │
│  (Vite + RTL)   │  HTTP  │  ┌────────────┐              │
└─────────────────┘        │  │ APScheduler│ (background) │
                           │  └────────────┘              │
                           │  ┌────────────┐              │
                           │  │ instagrapi │→ Instagram API│
                           │  └────────────┘              │
                           │  ┌────────────┐              │
                           │  │ Playwright │→ Real Browser │
                           │  └────────────┘              │
                           │  ┌────────────┐              │
                           │  │ PostgreSQL │              │
                           │  └────────────┘              │
                           └──────────────────────────────┘
```

### تشفير البيانات
جميع البيانات الحساسة مشفرة بـ **Fernet** (AES-128-CBC + HMAC-SHA256):
- `encrypted_password` — كلمة مرور Instagram
- `encrypted_session` — ملف الجلسة (cookies + settings)
- `encrypted_proxy` — بيانات البروكسي
- `encrypted_totp_secret` — مفتاح TOTP للـ 2FA

---

## API Documentation

الـ API التلقائية متاحة على `/api/docs` (Swagger UI) بعد تشغيل الـ backend.

### Endpoints الرئيسية

| Method | Path | الوصف |
|--------|------|-------|
| `POST` | `/api/auth/login` | تسجيل دخول → JWT |
| `GET` | `/api/accounts` | قائمة الحسابات |
| `POST` | `/api/accounts/login/password` | ربط حساب بكلمة المرور |
| `POST` | `/api/accounts/login/playwright` | ربط حساب بـ Playwright |
| `POST` | `/api/accounts/totp/preview` | معاينة رمز TOTP |
| `PATCH` | `/api/accounts/{id}/totp` | حفظ/حذف مفتاح TOTP |
| `PATCH` | `/api/accounts/{id}/proxy` | تحديث البروكسي |
| `GET` | `/api/targets` | قائمة الحسابات المستهدفة |
| `POST` | `/api/runs/trigger` | تشغيل يدوي |
| `GET` | `/api/logs` | سجل الإعجابات |
| `GET` | `/api/stats` | إحصاءات الاستخدام |

---

## الأمان | Security

- كلمات المرور وملفات الجلسة **مُشفَّرة دائماً** قبل التخزين
- مفاتيح Fernet و JWT يجب أن تكون **ثابتة** — تغييرها يُبطل كل الجلسات
- الـ dashboard محمي بـ **JWT Bearer token**
- معدلات الإعجاب محدودة لتقليل خطر الحظر
- تأخيرات عشوائية بين الإعجابات لمحاكاة السلوك البشري
- Playwright يستخدم بصمة متصفح حقيقية

---

## إخلاء المسؤولية | Disclaimer

هذا المشروع للأغراض التعليمية والشخصية فقط. استخدامه قد يخالف شروط خدمة Instagram.  
استخدمه على مسؤوليتك الخاصة.

---

## الترخيص | License

MIT
