import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ScheduleSettings, api } from '../api/client';

export default function Schedule() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<ScheduleSettings>({
    queryKey: ['schedule'],
    queryFn: async () => (await api.get<ScheduleSettings>('/settings/schedule')).data,
  });
  const [form, setForm] = useState<ScheduleSettings | null>(null);

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const save = useMutation({
    mutationFn: async () =>
      (await api.put<ScheduleSettings>('/settings/schedule', form)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedule'] }),
  });

  const runNow = useMutation({
    mutationFn: async () => (await api.post('/settings/schedule/run-now')).data,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (form) save.mutate();
  };

  if (isLoading || !form) return <p className="text-slate-400">جارٍ التحميل...</p>;

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-3xl font-bold">الجدولة والحدود</h1>

      <form onSubmit={submit} className="card space-y-6">

        {/* ── Auto-schedule toggle ── */}
        <Toggle
          label="تفعيل التشغيل التلقائي في الخلفية"
          description="يُشغّل المهمة تلقائياً كل عدد ساعات محدد"
          checked={form.enabled}
          onChange={(v) => setForm({ ...form, enabled: v })}
        />

        {/* ── Warm-up toggle ── */}
        <div className="border-t border-slate-800 pt-5">
          <Toggle
            label="التصفح التمهيدي (Warm-up)"
            description="يتصفح الفيد والاستكشاف عشوائياً قبل التفاعل — يقلل احتمال الكشف"
            checked={form.warmup_enabled}
            onChange={(v) => setForm({ ...form, warmup_enabled: v })}
            color="blue"
          />
        </div>

        {/* ── New-account mode toggle ── */}
        <div className="border-t border-slate-800 pt-5">
          <Toggle
            label="وضع الحساب الجديد"
            description="يخفض الحدود تلقائياً إلى النصف للحسابات الأقل من 30 يوماً — يقلل خطر الحظر"
            checked={form.new_account_mode}
            onChange={(v) => setForm({ ...form, new_account_mode: v })}
            color="orange"
          />
        </div>

        {/* ── Active hours window ── */}
        <div className="border-t border-slate-800 pt-5 space-y-3">
          <div>
            <p className="text-sm font-medium text-slate-300">نافذة ساعات النشاط (توقيت UTC)</p>
            <p className="text-xs text-slate-500 mt-0.5">
              البوت لن يعمل تلقائياً خارج هذه النافذة — يحاكي ساعات استخدام بشري طبيعي
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <NumberField
              label="من الساعة (UTC)"
              value={form.active_hours_start}
              min={0}
              max={23}
              onChange={(v) => setForm({ ...form, active_hours_start: v })}
              suffix="ص/م"
            />
            <NumberField
              label="إلى الساعة (UTC)"
              value={form.active_hours_end}
              min={0}
              max={23}
              onChange={(v) => setForm({ ...form, active_hours_end: v })}
              suffix="ص/م"
            />
          </div>
          <p className="text-xs text-slate-600">
            الإعداد الحالي: من{' '}
            <span className="text-slate-400">{formatHour(form.active_hours_start)}</span>
            {' '}إلى{' '}
            <span className="text-slate-400">{formatHour(form.active_hours_end)}</span>
            {' '}UTC
          </p>
        </div>

        {/* ── Rate limits ── */}
        <div className="border-t border-slate-800 pt-5">
          <p className="text-sm font-medium text-slate-300 mb-4">حدود التفاعل</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <NumberField
              label="الفاصل بين التشغيلات (ساعات)"
              value={form.interval_hours}
              min={1}
              max={168}
              onChange={(v) => setForm({ ...form, interval_hours: v })}
            />
            <NumberField
              label="الحد اليومي للإعجابات"
              value={form.daily_like_limit}
              min={1}
              max={500}
              onChange={(v) => setForm({ ...form, daily_like_limit: v })}
            />
            <NumberField
              label="الحد بالساعة للإعجابات"
              value={form.hourly_like_limit}
              min={1}
              max={100}
              onChange={(v) => setForm({ ...form, hourly_like_limit: v })}
            />
            <NumberField
              label="أقل تأخير بين الإجراءات (ثوانٍ)"
              value={form.min_delay_seconds}
              min={5}
              max={600}
              onChange={(v) => setForm({ ...form, min_delay_seconds: v })}
            />
            <NumberField
              label="أكبر تأخير بين الإجراءات (ثوانٍ)"
              value={form.max_delay_seconds}
              min={5}
              max={600}
              onChange={(v) => setForm({ ...form, max_delay_seconds: v })}
            />
          </div>
        </div>

        {/* ── Safe limits guide ── */}
        <div className="border-t border-slate-800 pt-4">
          <p className="text-xs text-slate-500 font-medium mb-2">دليل الحدود الآمنة:</p>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <SafeHint label="حسابات جديدة" daily="30–50" hourly="5–8" />
            <SafeHint label="حسابات متوسطة" daily="50–100" hourly="10–15" color="yellow" />
            <SafeHint label="حسابات قديمة" daily="100–200" hourly="15–25" color="green" />
          </div>
        </div>

        <div className="flex gap-2 pt-2">
          <button type="submit" className="btn-primary" disabled={save.isPending}>
            حفظ
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => runNow.mutate()}
            disabled={runNow.isPending}
          >
            {runNow.isPending ? 'جارٍ التشغيل...' : 'تشغيل الآن لكل الحسابات'}
          </button>
        </div>

        {save.isSuccess && <p className="text-sm text-green-400">تم الحفظ.</p>}
        {runNow.isSuccess && <p className="text-sm text-green-400">تم تشغيل المهمة.</p>}
      </form>
    </div>
  );
}

function formatHour(h: number): string {
  const period = h < 12 ? 'صباحاً' : 'مساءً';
  const display = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${display}:00 ${period}`;
}

function SafeHint({
  label,
  daily,
  hourly,
  color = 'slate',
}: {
  label: string;
  daily: string;
  hourly: string;
  color?: 'slate' | 'yellow' | 'green';
}) {
  const bg = { slate: 'bg-slate-800', yellow: 'bg-yellow-900/30', green: 'bg-green-900/30' }[color];
  const text = { slate: 'text-slate-400', yellow: 'text-yellow-300', green: 'text-green-300' }[color];
  return (
    <div className={`${bg} rounded-lg p-2 space-y-0.5`}>
      <p className={`font-medium ${text}`}>{label}</p>
      <p className="text-slate-500">يومي: {daily}</p>
      <p className="text-slate-500">بالساعة: {hourly}</p>
    </div>
  );
}

/* ── Toggle ──────────────────────────────────────────────────────────────── */
function Toggle({
  label,
  description,
  checked,
  onChange,
  color = 'pink',
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  color?: 'pink' | 'blue' | 'orange';
}) {
  const activeColor = { pink: '#e1306c', blue: '#2563eb', orange: '#ea580c' }[color];
  return (
    <div
      className="flex items-center justify-between gap-4 cursor-pointer select-none"
      onClick={() => onChange(!checked)}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-snug">{label}</p>
        {description && (
          <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{description}</p>
        )}
      </div>
      <div
        dir="ltr"
        className="shrink-0 w-11 h-6 rounded-full flex items-center px-1 transition-colors duration-200"
        style={{ backgroundColor: checked ? activeColor : '#334155' }}
      >
        <div
          className="w-4 h-4 rounded-full bg-white shadow transition-transform duration-200"
          style={{ transform: checked ? 'translateX(20px)' : 'translateX(0)' }}
        />
      </div>
    </div>
  );
}

/* ── NumberField ─────────────────────────────────────────────────────────── */
function NumberField({
  label,
  value,
  min,
  max,
  onChange,
  suffix,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
  suffix?: string;
}) {
  return (
    <label className="block">
      <span className="text-sm text-slate-300">{label}</span>
      <div className="flex items-center gap-2 mt-1">
        <input
          type="number"
          min={min}
          max={max}
          className="input flex-1"
          value={value}
          onChange={(e) => onChange(parseInt(e.target.value, 10) || min)}
        />
        {suffix && <span className="text-xs text-slate-500 shrink-0">{suffix}</span>}
      </div>
    </label>
  );
}
