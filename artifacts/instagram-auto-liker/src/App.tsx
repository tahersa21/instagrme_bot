import { Navigate, Route, Routes } from 'react-router-dom';
import { auth } from './api/client';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Targets from './pages/Targets';
import Schedule from './pages/Schedule';
import Logs from './pages/Logs';
import IgLogin from './pages/IgLogin';
import Analytics from './pages/Analytics';

function RequireAuth({ children }: { children: JSX.Element }) {
  return auth.isAuthed() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="ig-login" element={<IgLogin />} />
        <Route path="accounts/:accountId/targets" element={<Targets />} />
        <Route path="accounts/:accountId/logs" element={<Logs />} />
        <Route path="schedule" element={<Schedule />} />
        <Route path="analytics" element={<Analytics />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
