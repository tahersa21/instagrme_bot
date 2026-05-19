import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type SmsProvider } from '../api/client';

export default function SmsProviders() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ['sms-providers'],
    queryFn: async () => (await api.get<SmsProvider[]>('/sms-providers')).data,
  });

  const [name, setName] = useState('');
  const [providerType, setProviderType] = useState<'sms-activate' | '5sim'>('5sim');
  const [apiKey, setApiKey] = useState('');
  const [country, setCountry] = useState('0');
  const [isDefault, setIsDefault] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: async () =>
      (
        await api.post<SmsProvider>('/sms-providers', {
          name,
          provider_type: providerType,
          api_key: apiKey,
          country_code: country,
          is_default: isDefault,
        })
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sms-providers'] });
      setName('');
      setApiKey('');
      setCountry('0');
      setIsDefault(false);
      setErr(null);
    },
    onError: (e: unknown) => {
      const msg =
        (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'فشل الإضافة';
      setErr(msg);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: number) => api.delete(`/sms-providers/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sms-providers'] }),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    createMut.mutate();
  };

  return (
    <div className="space-y-8 max-w-4xl">
      <header>
        <h1 className="text-2xl font-bold mb-1">مزوّدو SMS للتحقق</h1>
        <p className="text-sm text-slate-400">
          أضف مفاتيح API الخاصة بـ sms-activate أو 5sim لاستلام أرقام مؤقتة عند طلب Instagram للتحقق الهاتفي.
        </p>
      </header>

      <form onSubmit={onSubmit} className="card p-6 space-y-4">
        <h2 className="font-semibold">إضافة مزوّد جديد</h2>
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-sm text-slate-300">اسم وصفي</span>
            <input
              className="input mt-1 w-full"
              placeholder="مثلاً: 5sim الأساسي"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="block">
            <span className="text-sm text-slate-300">المزوّد</span>
            <select
              className="input mt-1 w-full"
              value={providerType}
              onChange={(e) => setProviderType(e.target.value as 'sms-activate' | '5sim')}
            >
              <option value="5sim">5sim</option>
              <option value="sms-activate">sms-activate</option>
            </select>
          </label>
        </div>
        <label className="block">
          <span className="text-sm text-slate-300">API Key</span>
          <input
            type="password"
            className="input mt-1 w-full font-mono text-xs"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            required
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-300">رمز الدولة (0 = أي)</span>
          <input
            className="input mt-1 w-full"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
          />
          <span className="text-xs text-slate-500 mt-1 block">
            لـ 5sim استخدم اسم الدولة (مثل russia أو any). لـ sms-activate استخدم رقماً (0 = أي).
          </span>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
          />
          <span>اجعله المزوّد الافتراضي</span>
        </label>
        {err && <p className="text-red-400 text-sm">{err}</p>}
        <button className="btn-primary" disabled={createMut.isPending}>
          {createMut.isPending ? 'جارٍ الإضافة...' : 'إضافة'}
        </button>
      </form>

      <section className="space-y-3">
        <h2 className="font-semibold">المزوّدون المسجّلون</h2>
        {!data?.length && <p className="text-slate-400 text-sm">لا يوجد مزوّدون بعد.</p>}
        {data?.map((s) => (
          <div key={s.id} className="card p-4 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold">{s.name}</span>
                <span className="text-xs bg-slate-700 px-2 py-0.5 rounded">{s.provider_type}</span>
                {s.is_default && (
                  <span className="text-xs bg-ig-pink/20 text-ig-pink px-2 py-0.5 rounded">
                    افتراضي
                  </span>
                )}
              </div>
              <div className="text-xs text-slate-400 mt-1">الدولة: {s.country_code}</div>
            </div>
            <button
              className="btn-secondary text-sm"
              onClick={() => {
                if (confirm(`حذف المزوّد ${s.name}؟`)) deleteMut.mutate(s.id);
              }}
            >
              حذف
            </button>
          </div>
        ))}
      </section>
    </div>
  );
}
