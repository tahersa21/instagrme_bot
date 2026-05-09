import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { LikeLog, Run, api } from '../api/client';

export default function Logs() {
  const { accountId } = useParams<{ accountId: string }>();

  const runs = useQuery<Run[]>({
    queryKey: ['runs', accountId],
    queryFn: async () => (await api.get<Run[]>(`/accounts/${accountId}/runs`)).data,
    enabled: !!accountId,
  });

  const logs = useQuery<LikeLog[]>({
    queryKey: ['logs', accountId],
    queryFn: async () => (await api.get<LikeLog[]>(`/accounts/${accountId}/logs`)).data,
    enabled: !!accountId,
  });

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">السجل</h1>

      <section>
        <h2 className="text-xl font-semibold mb-3">آخر التشغيلات</h2>
        <div className="card overflow-x-auto">
          {runs.isLoading && <p className="text-slate-400">جارٍ التحميل...</p>}
          {!runs.isLoading && (runs.data?.length ?? 0) === 0 && (
            <p className="text-slate-400">لا توجد تشغيلات بعد.</p>
          )}
          {(runs.data?.length ?? 0) > 0 && (
            <table className="w-full text-sm">
              <thead className="text-slate-400">
                <tr className="border-b border-slate-800">
                  <th className="text-right py-2">البداية</th>
                  <th className="text-right py-2">الحالة</th>
                  <th className="text-right py-2">المصدر</th>
                  <th className="text-right py-2">نجح</th>
                  <th className="text-right py-2">تجاوز</th>
                  <th className="text-right py-2">فشل</th>
                </tr>
              </thead>
              <tbody>
                {runs.data!.map((r) => (
                  <tr key={r.id} className="border-b border-slate-800 last:border-0">
                    <td className="py-2">{new Date(r.started_at).toLocaleString('ar')}</td>
                    <td className="py-2">{r.status}</td>
                    <td className="py-2">{r.triggered_by}</td>
                    <td className="py-2 text-green-400">{r.likes_succeeded}</td>
                    <td className="py-2 text-yellow-400">{r.likes_skipped}</td>
                    <td className="py-2 text-red-400">{r.likes_failed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-3">سجل الإعجابات</h2>
        <div className="card overflow-x-auto">
          {logs.isLoading && <p className="text-slate-400">جارٍ التحميل...</p>}
          {!logs.isLoading && (logs.data?.length ?? 0) === 0 && (
            <p className="text-slate-400">لا توجد إعجابات بعد.</p>
          )}
          {(logs.data?.length ?? 0) > 0 && (
            <table className="w-full text-sm">
              <thead className="text-slate-400">
                <tr className="border-b border-slate-800">
                  <th className="text-right py-2">الوقت</th>
                  <th className="text-right py-2">الحساب</th>
                  <th className="text-right py-2">المنشور</th>
                  <th className="text-right py-2">الحالة</th>
                </tr>
              </thead>
              <tbody>
                {logs.data!.map((l) => (
                  <tr key={l.id} className="border-b border-slate-800 last:border-0">
                    <td className="py-2">{new Date(l.created_at).toLocaleString('ar')}</td>
                    <td className="py-2">@{l.target_username}</td>
                    <td className="py-2">
                      {l.media_url ? (
                        <a
                          className="text-ig-pink hover:underline"
                          href={l.media_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          فتح
                        </a>
                      ) : (
                        l.media_id
                      )}
                    </td>
                    <td className="py-2">
                      {l.success ? (
                        <span className="text-green-400">نجح</span>
                      ) : l.skipped_reason ? (
                        <span className="text-yellow-400">تجاوز ({l.skipped_reason})</span>
                      ) : (
                        <span className="text-red-400">فشل ({l.error})</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
