import { FormEvent, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

type Mode = 'cookies' | 'password';

export default function IgLogin() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('cookies');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [cookiesJson, setCookiesJson] = useState('');
  const [proxy, setProxy] = useState('');
  const [info, setInfo] = useState<string | null>(null);
  const [infoType, setInfoType] = useState<'error' | 'warn'>('error');
  const [requires2FA, setRequires2FA] = useState(false);

  const loginPwd = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/accounts/login/password', {
        username,
        password,
        verification_code: verificationCode || null,
        proxy: proxy.trim() || null,
      });
      return data;
    },
    onSuccess: (data) => {
      if (data.requires_2fa) {
        setRequires2FA(true);
        setInfoType('warn');
        setInfo('Instagram يطلب رمز 2FA. أدخله أعلاه ثم اضغط دخول مجدداً.');
        return;
      }
      navigate('/');
    },
    onError: (err) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'فشل';
      setInfoType('error');
      setInfo(`خطأ: ${detail}`);
    },
  });

  const loginCookies = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/accounts/login/cookies', {
        username,
        cookies_json: cookiesJson,
        proxy: proxy.trim() || null,
      });
      return data;
    },
    onSuccess: () => navigate('/'),
    onError: (err) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'فشل';
      setInfoType('error');
      setInfo(`خطأ: ${detail}`);
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setInfo(null);
    if (mode === 'cookies') loginCookies.mutate();
    else loginPwd.mutate();
  };

  const isLoading = loginPwd.isPending || loginCookies.isPending;

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-3xl font-bold">تسجيل دخول حساب Instagram</h1>

      {/* Method tabs */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => { setMode('cookies'); setInfo(null); }}
          className={mode === 'cookies' ? 'btn-primary' : 'btn-secondary'}
        >
          كوكيز / ملف الجلسة ✓ موصى به
        </button>
        <button
          type="button"
          onClick={() => { setMode('password'); setInfo(null); }}
          className={mode === 'password' ? 'btn-primary' : 'btn-secondary'}
        >
          اسم مستخدم + كلمة سر
        </button>
      </div>

      {/* Cookies instructions */}
      {mode === 'cookies' && (
        <div className="card border-blue-700/40 bg-blue-900/10 text-blue-200 text-sm space-y-2">
          <p className="font-semibold">كيف تحصل على ملف الكوكيز؟</p>
          <ol className="list-decimal list-inside space-y-1 text-blue-300">
            <li>افتح Instagram في Chrome وسجّل دخولك</li>
            <li>
              ثبّت إضافة{' '}
              <a
                href="https://chrome.google.com/webstore/detail/editthiscookie"
                target="_blank"
                rel="noreferrer"
                className="underline hover:text-white"
              >
                EditThisCookie
              </a>
            </li>
            <li>انقر على الإضافة وانقر "Export" لتصدير الكوكيز كـ JSON</li>
            <li>الصق الـ JSON في الحقل أدناه</li>
          </ol>
          <p className="text-yellow-300 text-xs">
            ⚠️ هذه الطريقة هي الأكثر موثوقية — تسجيل الدخول بكلمة المرور يُحجب أحياناً من سيرفرات الاستضافة.
          </p>
        </div>
      )}

      {/* Password warning */}
      {mode === 'password' && (
        <div className="card border-yellow-700/40 bg-yellow-900/10 text-yellow-200 text-sm">
          ⚠️ قد يفشل تسجيل الدخول بكلمة المرور من سيرفرات الاستضافة بسبب حماية Instagram.
          إذا فشل، استخدم طريقة <strong>الكوكيز</strong> بدلاً من ذلك.
        </div>
      )}

      <form onSubmit={handleSubmit} className="card space-y-4">
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

        {mode === 'password' && (
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
                <span className="text-sm text-slate-300">رمز التحقق (2FA)</span>
                <input
                  className="input mt-1"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  placeholder="123456"
                />
              </label>
            )}
          </>
        )}

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

        {/* Optional proxy */}
        <div className="border-t border-slate-800 pt-4">
          <label className="block">
            <span className="text-sm text-slate-300">
              بروكسي (اختياري)
            </span>
            <input
              className="input mt-1 font-mono text-sm"
              value={proxy}
              onChange={(e) => setProxy(e.target.value)}
              placeholder="http://user:pass@host:port"
              dir="ltr"
            />
            <p className="text-xs text-slate-500 mt-1">
              يُوصى باستخدام بروكسي سكنيّ (Residential) من نفس بلد الحساب. يدعم http/socks5.
            </p>
          </label>
        </div>

        {info && (
          <p className={`text-sm ${infoType === 'error' ? 'text-red-400' : 'text-yellow-300'}`}>
            {info}
          </p>
        )}

        <button type="submit" disabled={isLoading} className="btn-primary w-full">
          {isLoading ? 'جارٍ المعالجة...' : 'تسجيل الدخول'}
        </button>
      </form>
    </div>
  );
}
