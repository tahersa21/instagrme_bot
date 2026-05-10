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

        {/* Auto-schedule toggle */}
        <Toggle
          label="تفعيل التشغيل التلقائي في الخلفية"
          description="يُشغّل المهمة تلقائياً كل عدد ساعات محدد"
          checked={form.enabled}
          onChange={(v) => setForm({ ...form, enabled: v })}
        />

        {/* Warm-up toggle */}
        <div className="border-t border-slate-800 pt-5">
          <Toggle
            label="التصفح التمهيدي (Warm-up)"
            description="يتصفح الفيد والاستكشاف وبعض الصفحات عشوائياً قبل التفاعل، لتقليل احتمال الكشف"
            checked={form.warmup_enabled}
            onChange={(v) => setForm({ ...form, warmup_enabled: v })}
            color="blue"
          />
          {form.warmup_enabled && (
            <p className="mt-2 text-xs text-slate-500">
              يختار البوت 2-3 إجراءات عشوائية: تصفح الفيد ← الاستكشاف ← الملف الشخصي ← الرسائل. المدة ~20-40 ثانية.
            </p>
          )}
        </div>

        {/* Rate limits */}
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
  color?: 'pink' | 'blue';
}) {
  const activeColor = color === 'blue' ? '#2563eb' : '#e1306c';
  return (
    <div
      className="flex items-center justify-between gap-4 cursor-pointer select-none"
      onClick={() => onChange(!checked)}
    >
      {/* Text — appears on the RIGHT in RTL (first child) */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-snug">{label}</p>
        {description && (
          <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{description}</p>
        )}
      </div>

      {/* Toggle track — appears on the LEFT in RTL (last child), dir=ltr so thumb moves correctly */}
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

function NumberField({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <span className="text-sm text-slate-300">{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        className="input mt-1"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10) || min)}
      />
    </label>
  );
}
