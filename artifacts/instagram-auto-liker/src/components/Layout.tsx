import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { auth } from '../api/client';

const navClass = ({ isActive }: { isActive: boolean }) =>
  `block px-4 py-2 rounded-lg ${
    isActive ? 'bg-ig-pink text-white' : 'text-slate-300 hover:bg-slate-800'
  }`;

export default function Layout() {
  const navigate = useNavigate();
  const handleLogout = () => {
    auth.logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-slate-900 border-l border-slate-800 p-4 space-y-6 shrink-0">
        <div>
          <Link to="/" className="text-xl font-bold text-ig-pink">
            ❤︎ Auto Liker
          </Link>
          <p className="text-xs text-slate-500 mt-1">للاستخدام الشخصي فقط</p>
        </div>
        <nav className="space-y-1">
          <NavLink to="/" end className={navClass}>
            لوحة التحكم
          </NavLink>
          <NavLink to="/ig-login" className={navClass}>
            تسجيل دخول Instagram
          </NavLink>
          <NavLink to="/schedule" className={navClass}>
            الجدولة والحدود
          </NavLink>
          <NavLink to="/analytics" className={navClass}>
            الإحصاءات
          </NavLink>
        </nav>
        <button
          onClick={handleLogout}
          className="btn-secondary w-full text-sm"
          type="button"
        >
          تسجيل خروج
        </button>
      </aside>
      <main className="flex-1 p-8 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
