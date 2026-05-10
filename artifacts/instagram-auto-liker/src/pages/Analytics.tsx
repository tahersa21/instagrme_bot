import { useQuery } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { StatsOverview, api } from '../api/client';

export default function Analytics() {
  const { data, isLoading } = useQuery<StatsOverview>({
    queryKey: ['stats'],
    queryFn: async () => (await api.get<StatsOverview>('/stats/overview')).data,
    refetchInterval: 60_000,
  });

  if (isLoading || !data) {
    return <p className="text-slate-400">جارٍ التحميل...</p>;
  }

  const maxLikes = Math.max(...data.by_day.map((d) => d.likes), 1);

  return (
    <div className="space-y-8 max-w-4xl">
      <h1 className="text-3xl font-bold">الإحصاءات والتحليلات</h1>

      {/* ── Headline stats ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="إعجابات اليوم" value={data.today_likes} color="pink" />
        <StatCard label="إعجابات آخر 7 أيام" value={data.total_7d} color="blue" />
        <StatCard label="معدل النجاح" value={`${data.success_rate}%`} color="green" />
        <StatCard label="حسابات نشطة" value={data.accounts_active} color="purple" />
      </div>

      {/* ── Daily bar chart ── */}
      <div className="card space-y-4">
        <p className="text-sm font-medium text-slate-300">الإعجابات اليومية — آخر 7 أيام</p>
        {data.by_day.every((d) => d.likes === 0) ? (
          <p className="text-slate-500 text-sm py-6 text-center">لا توجد بيانات بعد.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.by_day} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <XAxis
                dataKey="date"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickFormatter={(v: string) => {
                  const d = new Date(v);
                  return `${d.getDate()}/${d.getMonth() + 1}`;
                }}
              />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#94a3b8', fontSize: 12 }}
                itemStyle={{ color: '#e1306c' }}
                formatter={(v: number) => [`${v} إعجاب`, '']}
                labelFormatter={(label: string) => new Date(label).toLocaleDateString('ar')}
              />
              <Bar dataKey="likes" radius={[4, 4, 0, 0]}>
                {data.by_day.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={entry.likes === maxLikes ? '#e1306c' : '#3b82f6'}
                    fillOpacity={entry.likes === 0 ? 0.2 : 0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Per-account breakdown ── */}
      <div className="card space-y-4">
        <p className="text-sm font-medium text-slate-300">إعجابات لكل حساب — آخر 7 أيام</p>
        {data.by_account.length === 0 ? (
          <p className="text-slate-500 text-sm py-4 text-center">لا توجد بيانات بعد.</p>
        ) : (
          <div className="space-y-3">
            {data.by_account.map((acc) => {
              const pct = Math.round((acc.likes / (data.total_7d || 1)) * 100);
              return (
                <div key={acc.username} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-300">@{acc.username}</span>
                    <span className="text-slate-400">{acc.likes} إعجاب ({pct}%)</span>
                  </div>
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-ig-pink transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Info note ── */}
      <p className="text-xs text-slate-600 text-center">
        البيانات تُحدَّث تلقائياً كل دقيقة · التواريخ بتوقيت UTC
      </p>
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number | string;
  color: 'pink' | 'blue' | 'green' | 'purple';
}) {
  const colors = {
    pink: 'text-ig-pink',
    blue: 'text-blue-400',
    green: 'text-green-400',
    purple: 'text-purple-400',
  };
  return (
    <div className="card text-center space-y-1 py-5">
      <p className={`text-3xl font-bold ${colors[color]}`}>{value}</p>
      <p className="text-xs text-slate-400">{label}</p>
    </div>
  );
}
