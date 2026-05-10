import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Account, api } from '../api/client';

export default function Dashboard() {
  const qc = useQueryClient();
  const { data: accounts = [], isLoading } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: async () => (await api.get<Account[]>('/accounts')).data,
  });

  const triggerRun = useMutation({
    mutationFn: async (accountId: number) =>
      (await api.post(`/accounts/${accountId}/runs`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts'] }),
  });

  const deleteAccount = useMutation({
    mutationFn: async (accountId: number) => api.delete(`/accounts/${accountId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts'] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">لوحة التحكم</h1>
        <Link to="/ig-login" className="btn-primary">
          + إضافة حساب Instagram
        </Link>
      </div>

      <div className="card border-yellow-700/50 bg-yellow-900/10 text-yellow-200 text-sm">
        <strong className="font-bold">تحذير:</strong> الأتمتة تنتهك شروط استخدام Instagram
        وقد تؤدي إلى حظر الحساب. الاستخدام على مسؤوليتك.
      </div>

      {isLoading && <p className="text-slate-400">جارٍ التحميل...</p>}

      {!isLoading && accounts.length === 0 && (
        <div className="card text-center py-12">
          <p className="text-slate-400 mb-4">لا توجد حسابات Instagram مضافة بعد.</p>
          <Link to="/ig-login" className="btn-primary">
            أضف أول حساب
          </Link>
        </div>
      )}

      <div className="grid gap-4">
        {accounts.map((acc) => (
          <div key={acc.id} className="card flex items-center justify-between">
            <div>
              <p className="text-lg font-semibold">@{acc.username}</p>
              <p className="text-xs text-slate-500">
                آخر دخول:{' '}
                {acc.last_login_at ? new Date(acc.last_login_at).toLocaleString('ar') : '—'}
              </p>
              {acc.session_renewed_at && (
                <p className="text-xs text-teal-400 mt-0.5">
                  آخر تجديد تلقائي:{' '}
                  {new Date(acc.session_renewed_at).toLocaleString('ar')}
                </p>
              )}
              {acc.last_error && (
                <p className="text-xs text-red-400 mt-1">خطأ: {acc.last_error}</p>
              )}
              <div className="flex gap-1 flex-wrap mt-2">
                <span
                  className={`inline-block px-2 py-0.5 rounded text-xs ${
                    acc.is_active
                      ? 'bg-green-900/40 text-green-300'
                      : 'bg-red-900/40 text-red-300'
                  }`}
                >
                  {acc.is_active ? 'نشط' : 'غير نشط'}
                </span>
                {acc.session_renewed_at && (() => {
                  const days = (Date.now() - new Date(acc.session_renewed_at).getTime()) / 86_400_000;
                  return days <= 7 ? (
                    <span className="inline-block px-2 py-0.5 rounded text-xs bg-teal-900/40 text-teal-300">
                      جُدِّدت الجلسة تلقائياً
                    </span>
                  ) : null;
                })()}
              </div>
            </div>
            <div className="flex gap-2">
              <Link to={`/accounts/${acc.id}/targets`} className="btn-secondary text-sm">
                الحسابات المستهدفة
              </Link>
              <Link to={`/accounts/${acc.id}/logs`} className="btn-secondary text-sm">
                السجل
              </Link>
              <button
                type="button"
                onClick={() => triggerRun.mutate(acc.id)}
                disabled={triggerRun.isPending}
                className="btn-primary text-sm"
              >
                تشغيل الآن
              </button>
              <button
                type="button"
                onClick={() => {
                  if (confirm(`حذف الحساب @${acc.username}؟`)) deleteAccount.mutate(acc.id);
                }}
                className="btn-danger text-sm"
              >
                حذف
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
