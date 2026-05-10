import { FormEvent, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

type Mode = 'playwright' | 'cookies' | 'password';

export default function IgLogin() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('playwright');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [cookiesJson, setCookiesJson] = useState('');
  const [proxy, setProxy] = useState('');
  const [proxyType, setProxyType] = useState('residential');
  const [info, setInfo] = useState<string | null>(null);
  const [infoType, setInfoType] = useState<'error' | 'warn' | 'info'>('error');
  const [requires2FA, setRequires2FA] = useState(false);

  /* ── Playwright login ── */
  const loginPW = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/accounts/login/playwright', {
        username,
        password,
        verification_code: verificationCode || null,
        proxy: proxy.trim() || null,
        proxy_type: proxyType || null,
      });
      return data;
    },
    onSuccess: (data) => {
      if (data.requires_2fa) {
        setRequires2FA(true);
        setInfoType('warn');
        setInfo('Instagram يطلب رمز 2FA — أدخله أعلاه واضغط دخول مجدداً');
        return;
      }
      navigate('/');
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail ?? 'فشل تسجيل الدخول';
      setInfoType('error');
      setInfo(`خطأ: ${detail}`);
    },
  });

  /* ── Password login (instagrapi API) ── */
  const loginPwd = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/accounts/login/password', {
        username,
        password,
        verification_code: verificationCode || null,
        proxy: proxy.trim() || null,
        proxy_type: proxyType || null,
      });
      return data;
    },
    onSuccess: (data) => {
      if (data.requires_2fa) {
        setRequires2FA(true);
        setInfoType('warn');
        setInfo('Instagram يطلب رمز 2FA — أدخله أعلاه واضغط دخول مجدداً');
        return;
      }
      navigate('/');
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail ?? 'فشل';
      setInfoType('error');
      setInfo(`خطأ: ${detail}`);
    },
  });

  /* ── Cookies login ── */
  const loginCookies = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/accounts/login/cookies', {
        username,
        cookies_json: cookiesJson,
        proxy: proxy.trim() || null,
        proxy_type: proxyType || null,
      });
      return data;
    },
    onSuccess: () => navigate('/'),
    onError: (err: any) => {
      const detail = err?.response?.data?.detail ?? 'فشل';
      setInfoType('error');
      setInfo(`خطأ: ${detail}`);
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setInfo(null);
    if (mode === 'playwright') loginPW.mutate();
    else if (mode === 'cookies') loginCookies.mutate();
    else loginPwd.mutate();
  };

  const isLoading = loginPW.isPending || loginPwd.isPending || loginCookies.isPending;

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-3xl font-bold">تسجيل دخول حساب Instagram</h1>

      {/* ── Method tabs ── */}
      <div className="flex gap-2 flex-wrap">
        <TabBtn active={mode === 'playwright'} onClick={() => { setMode('playwright'); setInfo(null); setRequires2FA(false); }}>
          🌐 متصفح حقيقي <span className="text-xs opacity-70 mr-1">⭐ موصى به</span>
        </TabBtn>
        <TabBtn active={mode === 'cookies'} onClick={() => { setMode('cookies'); setInfo(null); setRequires2FA(false); }}>
          🍪 كوكيز / جلسة
        </TabBtn>
        <TabBtn active={mode === 'password'} onClick={() => { setMode('password'); setInfo(null); setRequires2FA(false); }}>
          🔑 كلمة مرور (API)
        </TabBtn>
      </div>

      {/* ── Mode descriptions ── */}
      {mode === 'playwright' && (
        <div className="card border-green-700/40 bg-green-900/10 text-sm space-y-3">
          <p className="font-semibold text-green-300">✓ تسجيل الدخول عبر متصفح Chromium حقيقي</p>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="space-y-1">
              <p className="text-green-400 font-medium">المميزات:</p>
              <ul className="text-slate-300 space-y-0.5">
                <li>• بصمة متصفح حقيقية (Canvas, WebGL)</li>
                <li>• كوكيز حقيقية من Chrome</li>
                <li>• أقل احتمالاً للكشف من Instagram</li>
                <li>• يدعم 2FA تلقائياً</li>
              </ul>
            </div>
            <div className="space-y-1">
              <p className="text-yellow-400 font-medium">ملاحظات:</p>
              <ul className="text-slate-400 space-y-0.5">
                <li>• يستغرق 15-30 ثانية</li>
                <li>• يحتاج موارد أكثر على السيرفر</li>
                <li>• يعمل على أي VPS يدعم headless Chrome</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {mode === 'cookies' && (
        <div className="card border-blue-700/40 bg-blue-900/10 text-blue-200 text-sm space-y-2">
          <p className="font-semibold">كيف تحصل على ملف الكوكيز؟</p>
          <ol className="list-decimal list-inside space-y-1 text-blue-300 text-xs">
            <li>افتح Instagram في Chrome وسجّل دخولك</li>
            <li>ثبّت إضافة <strong>EditThisCookie</strong> أو <strong>Cookie-Editor</strong></li>
            <li>انقر على الإضافة → Export → الصق الـ JSON أدناه</li>
          </ol>
        </div>
      )}

      {mode === 'password' && (
        <div className="card border-yellow-700/40 bg-yellow-900/10 text-yellow-200 text-sm">
          ⚠️ قد يفشل تسجيل الدخول بكلمة المرور من سيرفرات الاستضافة.
          استخدم <strong>المتصفح الحقيقي</strong> للحصول على أفضل النتائج.
        </div>
      )}

      <form onSubmit={handleSubmit} className="card space-y-4">

        {/* Username (always shown) */}
        <label className="block">
          <span className="text-sm text-slate-300">اسم مستخدم Instagram</span>
          <input
            className="input mt-1"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="my_username"
            required
          />
        </label>

        {/* Password (playwright + password modes) */}
        {(mode === 'playwright' || mode === 'password') && (
          <>
            <label className="block">
              <span className="text-sm text-slate-300">كلمة المرور</span>
              <input
                type="password"
                className="input mt-1"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>

            {requires2FA && (
              <label className="block">
                <span className="text-sm text-slate-300">رمز التحقق الثنائي (2FA)</span>
                <input
                  className="input mt-1"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  placeholder="123456"
                  maxLength={8}
                />
              </label>
            )}
          </>
        )}

        {/* Cookies mode */}
        {mode === 'cookies' && (
          <label className="block">
            <span className="text-sm text-slate-300">الصق JSON الكوكيز هنا</span>
            <textarea
              className="input mt-1 h-48 font-mono text-xs"
              value={cookiesJson}
              onChange={(e) => setCookiesJson(e.target.value)}
              placeholder={'[{"name":"sessionid","value":"..."},...]'}
              required
            />
          </label>
        )}

        {/* ── Proxy ── */}
        <div className="border-t border-slate-800 pt-4 space-y-3">
          <p className="text-sm text-slate-300">بروكسي (اختياري)</p>

          {/* Proxy type */}
          <div className="flex gap-2 flex-wrap">
            {[
              { key: 'mobile_4g',   label: '📱 جوال 4G', hint: '✓ الأفضل' },
              { key: 'residential', label: '🏠 سكني',    hint: '' },
              { key: 'datacenter',  label: '🖥 داتاسنتر', hint: '⚠️ خطر' },
            ].map(({ key, label, hint }) => (
              <button
                key={key}
                type="button"
                onClick={() => setProxyType(key)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                  proxyType === key
                    ? 'border-ig-pink bg-ig-pink/10 text-white'
                    : 'border-slate-700 text-slate-400 hover:border-slate-600'
                }`}
              >
                {label} {hint && <span className="opacity-60">{hint}</span>}
              </button>
            ))}
          </div>

          <input
            className="input font-mono text-sm"
            value={proxy}
            onChange={(e) => setProxy(e.target.value)}
            placeholder="http://user:pass@host:port  أو  socks5://host:port"
            dir="ltr"
          />
        </div>

        {/* Status message */}
        {isLoading && mode === 'playwright' && (
          <div className="flex items-center gap-3 text-sm text-blue-300 bg-blue-900/20 rounded-lg px-4 py-3">
            <span className="animate-spin text-lg">⏳</span>
            <span>
              جارٍ تشغيل المتصفح وتسجيل الدخول...
              <span className="block text-xs text-slate-400 mt-0.5">قد يستغرق هذا 15-30 ثانية</span>
            </span>
          </div>
        )}

        {info && (
          <p className={`text-sm ${
            infoType === 'error' ? 'text-red-400' :
            infoType === 'warn' ? 'text-yellow-300' :
            'text-blue-300'
          }`}>
            {info}
          </p>
        )}

        <button type="submit" disabled={isLoading} className="btn-primary w-full">
          {isLoading
            ? (mode === 'playwright' ? '🌐 جارٍ التشغيل...' : 'جارٍ المعالجة...')
            : mode === 'playwright'
              ? '🌐 تسجيل الدخول عبر المتصفح'
              : 'تسجيل الدخول'
          }
        </button>
      </form>
    </div>
  );
}

function TabBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
        active
          ? 'bg-ig-pink text-white'
          : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
      }`}
    >
      {children}
    </button>
  );
}
