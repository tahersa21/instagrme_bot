import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { auth } from '../api/client';

const navClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
    isActive
      ? 'bg-gradient-to-l from-ig-pink/20 to-ig-pink/5 text-ig-pink border border-ig-pink/30'
      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
  }`;

export default function Layout() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-row-reverse">
      {/* Sidebar — right side for RTL */}
      <aside
        className="w-60 shrink-0 flex flex-col"
        style={{
          background: 'linear-gradient(180deg, #0a1120 0%, #070e1a 100%)',
          borderLeft: '1px solid #1e293b',
        }}
      >
        {/* Logo */}
        <div className="px-5 py-6 border-b border-slate-800/60">
          <div className="flex items-center gap-2">
            <span className="text-2xl">❤</span>
            <div>
              <p className="font-bold text-white leading-tight">Auto Liker</p>
              <p className="text-xs text-slate-500">لوحة التحكم</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider px-4 mb-2">
            القائمة
          </p>
          <NavLink to="/" end className={navClass}>
            <span>🏠</span> لوحة التحكم
          </NavLink>
          <NavLink to="/ig-login" className={navClass}>
            <span>🔑</span> ربط حساب Instagram
          </NavLink>
          <NavLink to="/schedule" className={navClass}>
            <span>⚙️</span> الجدولة والحدود
          </NavLink>
        </nav>

        {/* Logout */}
        <div className="px-3 py-4 border-t border-slate-800/60">
          <button
            onClick={() => { auth.logout(); navigate('/login'); }}
            className="btn-secondary w-full text-sm"
            type="button"
          >
            <span>↩</span> تسجيل خروج
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
