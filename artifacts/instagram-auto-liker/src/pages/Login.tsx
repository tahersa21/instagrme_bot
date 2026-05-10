import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../api/client';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await auth.login(username, password);
      navigate('/');
    } catch {
      setError('بيانات الدخول غير صحيحة');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{
        background: 'radial-gradient(ellipse at 60% 20%, rgba(131,58,180,0.15) 0%, transparent 60%), radial-gradient(ellipse at 20% 80%, rgba(225,48,108,0.1) 0%, transparent 50%), #020617',
      }}
    >
      {/* Glow ring */}
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4 text-3xl"
            style={{
              background: 'linear-gradient(135deg, #833ab4, #e1306c)',
              boxShadow: '0 8px 32px rgba(225,48,108,0.35)',
            }}
          >
            ❤
          </div>
          <h1 className="text-2xl font-bold text-white">Instagram Auto Liker</h1>
          <p className="text-sm text-slate-500 mt-1">لوحة التحكم</p>
        </div>

        {/* Card */}
        <form
          onSubmit={handleSubmit}
          className="card space-y-5"
          style={{ boxShadow: '0 20px 60px rgba(0,0,0,0.5)' }}
          aria-labelledby="login-title"
        >
          <div>
            <h2 id="login-title" className="text-base font-semibold text-slate-200">
              تسجيل الدخول
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              هذه ليست بيانات Instagram — هي بيانات لوحة التحكم المحلية.
            </p>
          </div>

          <label className="block">
            <span className="text-sm text-slate-400 font-medium">اسم المستخدم</span>
            <input
              type="text"
              className="input mt-1.5"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <label className="block">
            <span className="text-sm text-slate-400 font-medium">كلمة المرور</span>
            <input
              type="password"
              className="input mt-1.5"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          {error && (
            <div className="text-sm text-red-400 bg-red-950/40 border border-red-900/50 rounded-lg px-4 py-2.5">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3 text-base"
          >
            {loading ? 'جارٍ الدخول...' : 'دخول'}
          </button>
        </form>
      </div>
    </div>
  );
}
