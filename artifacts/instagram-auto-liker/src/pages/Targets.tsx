import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { Target, api } from '../api/client';

export default function Targets() {
  const { accountId } = useParams<{ accountId: string }>();
  const qc = useQueryClient();
  const [username, setUsername] = useState('');
  const [likesPerRun, setLikesPerRun] = useState(3);

  const { data: targets = [], isLoading } = useQuery<Target[]>({
    queryKey: ['targets', accountId],
    queryFn: async () => (await api.get<Target[]>(`/accounts/${accountId}/targets`)).data,
    enabled: !!accountId,
  });

  const create = useMutation({
    mutationFn: async () =>
      (await api.post<Target>(`/accounts/${accountId}/targets`, {
        username,
        likes_per_run: likesPerRun,
        is_enabled: true,
      })).data,
    onSuccess: () => {
      setUsername('');
      qc.invalidateQueries({ queryKey: ['targets', accountId] });
    },
  });

  const toggle = useMutation({
    mutationFn: async (t: Target) =>
      (await api.patch<Target>(`/accounts/${accountId}/targets/${t.id}`, {
        is_enabled: !t.is_enabled,
      })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['targets', accountId] }),
  });

  const remove = useMutation({
    mutationFn: async (id: number) => api.delete(`/accounts/${accountId}/targets/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['targets', accountId] }),
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (username.trim()) create.mutate();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">الحسابات المستهدفة</h1>

      <form onSubmit={submit} className="card flex flex-wrap gap-3 items-end">
        <label className="flex-1 min-w-[200px]">
          <span className="text-sm text-slate-300">اسم الحساب</span>
          <input
            className="input mt-1"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="natgeo"
            required
          />
        </label>
        <label>
          <span className="text-sm text-slate-300">إعجابات لكل تشغيل</span>
          <input
            type="number"
            min={1}
            max={20}
            className="input mt-1 w-32"
            value={likesPerRun}
            onChange={(e) => setLikesPerRun(parseInt(e.target.value, 10) || 1)}
          />
        </label>
        <button type="submit" className="btn-primary" disabled={create.isPending}>
          إضافة
        </button>
      </form>

      {isLoading && <p className="text-slate-400">جارٍ التحميل...</p>}

      <div className="card">
        {targets.length === 0 ? (
          <p className="text-slate-400 text-center py-4">لا توجد حسابات مستهدفة بعد.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-slate-400">
              <tr className="border-b border-slate-800">
                <th className="text-right py-2">الحساب</th>
                <th className="text-right py-2">إعجابات/تشغيل</th>
                <th className="text-right py-2">الحالة</th>
                <th className="text-right py-2"></th>
              </tr>
            </thead>
            <tbody>
              {targets.map((t) => (
                <tr key={t.id} className="border-b border-slate-800 last:border-0">
                  <td className="py-3">@{t.username}</td>
                  <td className="py-3">{t.likes_per_run}</td>
                  <td className="py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${
                        t.is_enabled
                          ? 'bg-green-900/40 text-green-300'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {t.is_enabled ? 'مفعّل' : 'معطّل'}
                    </span>
                  </td>
                  <td className="py-3 flex gap-2">
                    <button
                      type="button"
                      className="btn-secondary text-xs"
                      onClick={() => toggle.mutate(t)}
                    >
                      {t.is_enabled ? 'تعطيل' : 'تفعيل'}
                    </button>
                    <button
                      type="button"
                      className="btn-danger text-xs"
                      onClick={() => {
                        if (confirm(`حذف @${t.username}؟`)) remove.mutate(t.id);
                      }}
                    >
                      حذف
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
