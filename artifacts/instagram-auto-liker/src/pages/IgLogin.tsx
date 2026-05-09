import { FormEvent, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

type Mode = 'password' | 'cookies';

export default function IgLogin() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('password');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [cookiesJson, setCookiesJson] = useState('');
  const [info, setInfo] = useState<string | null>(null);
  const [requires2FA, setRequires2FA] = useState(false);

  const loginPwd = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/accounts/login/password', {
        username,
        password,
        verification_code: verificationCode || null,
      });
      return data;
    },
    onSuccess: (data) => {
      if (data.requires_2fa) {
        setRequires2FA(true);
        setInfo('Instagram يطلب رمز 2FA. أدخله أعلاه ثم اضغط دخول مجدداً.');
        return;
      }
      navigate('/');
    },
    onError: (err) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'فشل';
      setInfo(`خطأ: ${detail}`);
    },
  });

  const loginCookies = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/accounts/login/cookies', {
        username,
        cookies_json: cookiesJson,
      });
      return data;
    },
    onSuccess: () => navigate('/'),
    onError: (err) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'فشل';
      setInfo(`خطأ: ${detail}`);
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setInfo(null);
    if (mode === 'password') loginPwd.mutate();
    else loginCookies.mutate();
  };

  const isLoading = loginPwd.isPending || loginCookies.isPending;

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-3xl font-bold">تسجيل دخول حساب Instagram</h1>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setMode('password')}
          className={mode === 'password' ? 'btn-primary' : 'btn-secondary'}
        >
          اسم مستخدم + كلمة سر
        </button>
        <button
          type="button"
          onClick={() => setMode('cookies')}
          className={mode === 'cookies' ? 'btn-primary' : 'btn-secondary'}
        >
          كوكيز / ملف الجلسة
        </button>
      </div>

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
            <span className="text-sm text-slate-300">
              JSON للجلسة (إما instagrapi settings أو مصفوفة كوكيز فيها sessionid)
            </span>
            <textarea
              className="input mt-1 h-48 font-mono text-xs"
              value={cookiesJson}
              onChange={(e) => setCookiesJson(e.target.value)}
              placeholder={'{\n  "authorization_data": {...},\n  "cookies": {...}\n}'}
              required
            />
          </label>
        )}

        {info && <p className="text-sm text-yellow-300">{info}</p>}

        <button type="submit" disabled={isLoading} className="btn-primary w-full">
          {isLoading ? 'جارٍ المعالجة...' : 'تسجيل الدخول'}
        </button>
      </form>
    </div>
  );
}
