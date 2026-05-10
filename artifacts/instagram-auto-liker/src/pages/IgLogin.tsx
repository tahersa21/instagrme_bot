import { FormEvent, useEffect, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

type Mode = 'playwright' | 'cookies' | 'password';

/* ── Live TOTP code widget ───────────────────────────────────────────────── */
function TotpPreview({ secret }: { secret: string }) {
  const [code, setCode] = useState('------');
  const [remaining, setRemaining] = useState(30);

  useEffect(() => {
    if (!secret.trim()) {
      setCode('------');
      return;
    }
    // Simple HOTP/TOTP in browser using Web Crypto (avoid extra deps)
    // We call the backend preview endpoint for live validation
    let alive = true;
    const tick = () => {
      const now = Math.floor(Date.now() / 1000);
      const rem = 30 - (now % 30);
      if (alive) setRemaining(rem);
    };
    tick();
    const iv = setInterval(tick, 1000);
    return () => { alive = false; clearInterval(iv); };
  }, [secret]);

  // Generate code client-side via backend endpoint when secret changes
  const preview = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<{ code: string }>('/accounts/totp/preview', {
        totp_secret: secret.trim(),
      });
      return data.code;
    },
    onSuccess: (c) => setCode(c),
    onError: () => setCode('خطأ'),
  });

  useEffect(() => {
    if (secret.trim().length >= 16) {
      preview.mutate();
    } else {
      setCode('------');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [secret]);

  // Refresh code when the 30-second window resets
  useEffect(() => {
    if (remaining === 30 && secret.trim().length >= 16) {
      preview.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remaining]);

  const barPct = ((30 - remaining) / 30) * 100;
  const barColor = remaining <= 5 ? '#ef4444' : remaining <= 10 ? '#f59e0b' : '#22c55e';

  return (
    <div className="rounded-lg bg-slate-900 border border-slate-700 px-4 py-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400">الرمز الحالي (مباشر):</span>
        <span className="text-xs text-slate-500">يتجدد خلال {remaining}ث</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="font-mono text-2xl font-bold tracking-widest text-green-400 select-all">
          {code.length === 6 ? `${code.slice(0, 3)} ${code.slice(3)}` : code}
        </span>
      </div>
      {/* countdown bar */}
      <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-1000"
          style={{ width: `${barPct}%`, backgroundColor: barColor }}
        />
      </div>
    </div>
  );
}

/* ── Main page ───────────────────────────────────────────────────────────── */
export default function IgLogin() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('playwright');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [totpSecret, setTotpSecret] = useState('');
  const [showTotpField, setShowTotpField] = useState(false);
  const [cookiesJson, setCookiesJson] = useState('');
  const [proxy, setProxy] = useState('');
  const [proxyType, setProxyType] = useState('residential');
  const [info, setInfo] = useState<string | null>(null);
  const [infoType, setInfoType] = useState<'error' | 'warn' | 'info'>('error');
  const [requires2FA, setRequires2FA] = useState(false);

  const buildPayload = () => ({
    username,
    password,
    verification_code: verificationCode || null,
    totp_secret: totpSecret.trim().replace(/[\s-]/g, '') || null,
    proxy: proxy.trim() || null,
    proxy_type: proxyType || null,
  });

  /* ── Playwright login ── */
  const loginPW = useMutation({
    mutationFn: async () => (await api.post('/accounts/login/playwright', buildPayload())).data,
    onSuccess: (data) => {
      if (data.requires_2fa) {
        setRequires2FA(true);
        setInfoType('warn');
        setInfo('Instagram يطلب رمز 2FA — أدخل الرمز يدوياً أو أضف مفتاح TOTP');
        return;
      }
      navigate('/');
    },
    onError: (err: any) => {
      setInfoType('error');
      setInfo(`خطأ: ${err?.response?.data?.detail ?? 'فشل تسجيل الدخول'}`);
    },
  });

  /* ── Password (API) login ── */
  const loginPwd = useMutation({
    mutationFn: async () => (await api.post('/accounts/login/password', buildPayload())).data,
    onSuccess: (data) => {
      if (data.requires_2fa) {
        setRequires2FA(true);
        setInfoType('warn');
        setInfo('Instagram يطلب رمز 2FA — أدخل الرمز يدوياً أو أضف مفتاح TOTP');
        return;
      }
      navigate('/');
    },
    onError: (err: any) => {
      setInfoType('error');
      setInfo(`خطأ: ${err?.response?.data?.detail ?? 'فشل'}`);
    },
  });

  /* ── Cookies login ── */
  const loginCookies = useMutation({
    mutationFn: async () =>
      (await api.post('/accounts/login/cookies', {
        username,
        cookies_json: cookiesJson,
        proxy: proxy.trim() || null,
        proxy_type: proxyType || null,
      })).data,
    onSuccess: () => navigate('/'),
    onError: (err: any) => {
      setInfoType('error');
      setInfo(`خطأ: ${err?.response?.data?.detail ?? 'فشل'}`);
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

      {/* ── Tabs ── */}
      <div className="flex gap-2 flex-wrap">
        {([
          { key: 'playwright', label: '🌐 متصفح حقيقي', hint: '⭐ موصى به' },
          { key: 'cookies',    label: '🍪 كوكيز / جلسة', hint: '' },
          { key: 'password',   label: '🔑 كلمة مرور (API)', hint: '' },
        ] as { key: Mode; label: string; hint: string }[]).map(({ key, label, hint }) => (
          <button
            key={key}
            type="button"
            onClick={() => { setMode(key); setInfo(null); setRequires2FA(false); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === key ? 'bg-ig-pink text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {label}
            {hint && <span className="text-xs opacity-60 mr-1">{hint}</span>}
          </button>
        ))}
      </div>

      {/* ── Mode notes ── */}
      {mode === 'playwright' && (
        <div className="card border-green-700/40 bg-green-900/10 text-sm space-y-2">
          <p className="font-semibold text-green-300">✓ متصفح Chromium حقيقي — بصمة حقيقية</p>
          <p className="text-xs text-slate-400">بصمة Canvas/WebGL حقيقية · كوكيز حقيقية · 2FA تلقائي · يستغرق 15-30 ثانية</p>
        </div>
      )}
      {mode === 'cookies' && (
        <div className="card border-blue-700/40 bg-blue-900/10 text-blue-200 text-sm space-y-2">
          <p className="font-semibold">كيف تحصل على الكوكيز؟</p>
          <ol className="list-decimal list-inside text-xs text-blue-300 space-y-1">
            <li>افتح Instagram في Chrome وسجّل دخولك</li>
            <li>ثبّت إضافة Cookie-Editor أو EditThisCookie</li>
            <li>اضغط Export والصق الـ JSON أدناه</li>
          </ol>
        </div>
      )}
      {mode === 'password' && (
        <div className="card border-yellow-700/40 bg-yellow-900/10 text-yellow-200 text-sm">
          ⚠️ قد يفشل من سيرفرات الاستضافة — استخدم <strong>المتصفح الحقيقي</strong> للحصول على أفضل النتائج.
        </div>
      )}

      <form onSubmit={handleSubmit} className="card space-y-4">

        {/* Username */}
        <label className="block">
          <span className="text-sm text-slate-300">اسم مستخدم Instagram</span>
          <input className="input mt-1" value={username} onChange={(e) => setUsername(e.target.value)}
            placeholder="my_username" required />
        </label>

        {/* Password (playwright + password modes) */}
        {(mode === 'playwright' || mode === 'password') && (
          <label className="block">
            <span className="text-sm text-slate-300">كلمة المرور</span>
            <input type="password" className="input mt-1" value={password}
              onChange={(e) => setPassword(e.target.value)} required />
          </label>
        )}

        {/* Cookies textarea */}
        {mode === 'cookies' && (
          <label className="block">
            <span className="text-sm text-slate-300">الصق JSON الكوكيز هنا</span>
            <textarea className="input mt-1 h-40 font-mono text-xs" value={cookiesJson}
              onChange={(e) => setCookiesJson(e.target.value)}
              placeholder={'[{"name":"sessionid","value":"..."},...]'} required />
          </label>
        )}

        {/* ── 2FA Section (password + playwright modes) ── */}
        {(mode === 'playwright' || mode === 'password') && (
          <div className="border border-slate-700 rounded-xl p-4 space-y-3">
            {/* Toggle header */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-200">التحقق الثنائي (2FA)</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {showTotpField
                    ? 'مفتاح TOTP محفوظ — يُولَّد الرمز تلقائياً عند كل دخول'
                    : 'أضف مفتاح TOTP لتسجيل الدخول التلقائي بدون تدخل يدوي'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowTotpField((v) => !v)}
                className={`relative w-11 h-6 rounded-full transition-colors focus:outline-none flex-shrink-0 ${
                  showTotpField ? 'bg-ig-pink' : 'bg-slate-700'
                }`}
                dir="ltr"
              >
                <span
                  className="absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform"
                  style={{ transform: showTotpField ? 'translateX(22px)' : 'translateX(4px)' }}
                />
              </button>
            </div>

            {showTotpField && (
              <div className="space-y-3">
                {/* TOTP Secret field */}
                <label className="block">
                  <span className="text-xs text-slate-400">
                    مفتاح TOTP السري (Base32) — من تطبيق Google Authenticator أو Authy
                  </span>
                  <div className="flex gap-2 mt-1">
                    <input
                      className="input flex-1 font-mono text-sm tracking-widest"
                      value={totpSecret}
                      onChange={(e) => setTotpSecret(e.target.value)}
                      placeholder="JBSWY3DPEHPK3PXP"
                      dir="ltr"
                      autoComplete="off"
                    />
                  </div>
                  <p className="text-xs text-slate-600 mt-1">
                    انتقل إلى Instagram ← الإعدادات ← الأمان ← التحقق بخطوتين ← التطبيق ← انسخ المفتاح
                  </p>
                </label>

                {/* Live TOTP preview */}
                {totpSecret.trim().length >= 16 && (
                  <TotpPreview secret={totpSecret} />
                )}

                {/* 2FA reminder */}
                <div className="text-xs text-slate-500 bg-slate-900 rounded-lg px-3 py-2 space-y-1">
                  <p className="text-slate-400 font-medium">كيف تحصل على المفتاح من Instagram؟</p>
                  <ol className="list-decimal list-inside space-y-0.5">
                    <li>الإعدادات → الأمان → التحقق بخطوتين</li>
                    <li>اختر &quot;تطبيق المصادقة&quot;</li>
                    <li>اضغط &quot;لا أستطيع مسح الرمز&quot; لرؤية المفتاح النصي</li>
                    <li>انسخ المفتاح Base32 والصقه هنا</li>
                  </ol>
                </div>
              </div>
            )}

            {/* Manual 2FA code (fallback if no TOTP secret) */}
            {requires2FA && !showTotpField && (
              <label className="block">
                <span className="text-sm text-slate-300">رمز التحقق اليدوي (2FA)</span>
                <input className="input mt-1" value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  placeholder="123456" maxLength={8} />
              </label>
            )}
          </div>
        )}

        {/* ── Proxy ── */}
        <div className="border-t border-slate-800 pt-4 space-y-3">
          <p className="text-sm text-slate-300">بروكسي (اختياري)</p>
          <div className="flex gap-2 flex-wrap">
            {[
              { key: 'mobile_4g',   label: '📱 جوال 4G',  hint: '✓ الأفضل' },
              { key: 'residential', label: '🏠 سكني',     hint: '' },
              { key: 'datacenter',  label: '🖥 داتاسنتر',  hint: '⚠️ خطر' },
            ].map(({ key, label, hint }) => (
              <button key={key} type="button" onClick={() => setProxyType(key)}
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
          <input className="input font-mono text-sm" value={proxy}
            onChange={(e) => setProxy(e.target.value)}
            placeholder="http://user:pass@host:port  أو  socks5://host:port" dir="ltr" />
        </div>

        {/* Loading indicator */}
        {isLoading && mode === 'playwright' && (
          <div className="flex items-center gap-3 text-sm text-blue-300 bg-blue-900/20 rounded-lg px-4 py-3">
            <span className="animate-spin text-lg">⏳</span>
            <span>
              جارٍ تشغيل المتصفح وتسجيل الدخول...
              <span className="block text-xs text-slate-400 mt-0.5">قد يستغرق 15-30 ثانية</span>
            </span>
          </div>
        )}

        {info && (
          <p className={`text-sm ${
            infoType === 'error' ? 'text-red-400' :
            infoType === 'warn' ? 'text-yellow-300' : 'text-blue-300'
          }`}>
            {info}
          </p>
        )}

        <button type="submit" disabled={isLoading} className="btn-primary w-full">
          {isLoading
            ? (mode === 'playwright' ? '🌐 جارٍ التشغيل...' : 'جارٍ المعالجة...')
            : mode === 'playwright' ? '🌐 تسجيل الدخول عبر المتصفح' : 'تسجيل الدخول'}
        </button>
      </form>
    </div>
  );
}
