import { useState } from 'react';
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
          <AccountCard
            key={acc.id}
            acc={acc}
            onRun={() => triggerRun.mutate(acc.id)}
            onDelete={() => {
              if (confirm(`حذف الحساب @${acc.username}؟`)) deleteAccount.mutate(acc.id);
            }}
            runPending={triggerRun.isPending}
            onProxyUpdate={() => qc.invalidateQueries({ queryKey: ['accounts'] })}
          />
        ))}
      </div>
    </div>
  );
}

function AccountCard({
  acc,
  onRun,
  onDelete,
  runPending,
  onProxyUpdate,
}: {
  acc: Account;
  onRun: () => void;
  onDelete: () => void;
  runPending: boolean;
  onProxyUpdate: () => void;
}) {
  const [showProxy, setShowProxy] = useState(false);
  const [proxyInput, setProxyInput] = useState('');
  const [proxyMsg, setProxyMsg] = useState<{ text: string; ok: boolean } | null>(null);

  const saveProxy = useMutation({
    mutationFn: async (proxy: string | null) =>
      (await api.patch<Account>(`/accounts/${acc.id}/proxy`, { proxy })).data,
    onSuccess: () => {
      setProxyMsg({ text: proxy ? 'تم حفظ البروكسي.' : 'تم حذف البروكسي.', ok: true });
      onProxyUpdate();
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail ?? 'حدث خطأ';
      setProxyMsg({ text: detail, ok: false });
    },
  });

  const proxy = proxyInput.trim() || null;

  return (
    <div className="card space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-lg font-semibold">@{acc.username}</p>
            <span
              className={`px-2 py-0.5 rounded text-xs ${
                acc.is_active
                  ? 'bg-green-900/40 text-green-300'
                  : 'bg-red-900/40 text-red-300'
              }`}
            >
              {acc.is_active ? 'نشط' : 'غير نشط'}
            </span>
            {acc.has_proxy && (
              <span className="px-2 py-0.5 rounded text-xs bg-blue-900/40 text-blue-300">
                🌐 بروكسي مفعّل
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            آخر دخول:{' '}
            {acc.last_login_at ? new Date(acc.last_login_at).toLocaleString('ar') : '—'}
          </p>
          {acc.last_error && (
            <p className="text-xs text-red-400 mt-1">خطأ: {acc.last_error}</p>
          )}
        </div>

        <div className="flex gap-2 flex-wrap justify-end">
          <Link to={`/accounts/${acc.id}/targets`} className="btn-secondary text-sm">
            الحسابات المستهدفة
          </Link>
          <Link to={`/accounts/${acc.id}/logs`} className="btn-secondary text-sm">
            السجل
          </Link>
          <button
            type="button"
            onClick={() => { setShowProxy(!showProxy); setProxyMsg(null); }}
            className="btn-secondary text-sm"
          >
            🌐 بروكسي
          </button>
          <button
            type="button"
            onClick={onRun}
            disabled={runPending}
            className="btn-primary text-sm"
          >
            تشغيل الآن
          </button>
          <button type="button" onClick={onDelete} className="btn-danger text-sm">
            حذف
          </button>
        </div>
      </div>

      {/* Proxy panel */}
      {showProxy && (
        <div className="border-t border-slate-800 pt-4 space-y-3">
          <p className="text-sm font-medium text-slate-300">إعداد البروكسي</p>

          <div className="text-xs text-slate-400 space-y-1">
            <p>الصيغ المدعومة:</p>
            <div className="font-mono bg-slate-900 rounded px-3 py-2 space-y-1">
              <p>http://user:pass@host:port</p>
              <p>socks5://user:pass@host:port</p>
              <p>http://host:port</p>
            </div>
          </div>

          <div className="flex gap-2 flex-wrap items-end">
            <input
              className="input flex-1 min-w-[260px] font-mono text-sm"
              placeholder="http://user:pass@1.2.3.4:8080"
              value={proxyInput}
              onChange={(e) => setProxyInput(e.target.value)}
              dir="ltr"
            />
            <button
              type="button"
              className="btn-primary text-sm"
              onClick={() => saveProxy.mutate(proxy)}
              disabled={saveProxy.isPending}
            >
              {saveProxy.isPending ? '...' : 'حفظ'}
            </button>
            {acc.has_proxy && (
              <button
                type="button"
                className="btn-danger text-sm"
                onClick={() => { setProxyInput(''); saveProxy.mutate(null); }}
                disabled={saveProxy.isPending}
              >
                حذف البروكسي
              </button>
            )}
          </div>

          {proxyMsg && (
            <p className={`text-xs ${proxyMsg.ok ? 'text-green-400' : 'text-red-400'}`}>
              {proxyMsg.text}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
