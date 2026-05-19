import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type Domain } from '../api/client';

export default function Domains() {
  const qc = useQueryClient();
  const { data: domains } = useQuery({
    queryKey: ['domains'],
    queryFn: async () => (await api.get<Domain[]>('/domains')).data,
  });

  const [name, setName] = useState('');
  const [mailgunDomain, setMailgunDomain] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const [notes, setNotes] = useState('');
  const [err, setErr] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<Domain>('/domains', {
        name,
        mailgun_domain: mailgunDomain,
        mailgun_api_key: apiKey,
        is_default: isDefault,
        notes: notes || null,
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['domains'] });
      setName('');
      setMailgunDomain('');
      setApiKey('');
      setIsDefault(false);
      setNotes('');
      setErr(null);
    },
    onError: (e: unknown) => {
      const msg =
        (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'فشل الإضافة';
      setErr(msg);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: number) => api.delete(`/domains/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['domains'] }),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    createMut.mutate();
  };

  return (
    <div className="space-y-8 max-w-4xl">
      <header>
        <h1 className="text-2xl font-bold mb-1">النطاقات (Mailgun)</h1>
        <p className="text-sm text-slate-400">
          أضف نطاقاتك المسجّلة في Mailgun لاستقبال رسائل التحقق عند إنشاء حسابات Instagram.
        </p>
      </header>

      <form onSubmit={onSubmit} className="card p-6 space-y-4">
        <h2 className="font-semibold">إضافة نطاق جديد</h2>
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-sm text-slate-300">اسم النطاق</span>
            <input
              className="input mt-1 w-full"
              placeholder="mydomain.com"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="block">
            <span className="text-sm text-slate-300">Mailgun Domain</span>
            <input
              className="input mt-1 w-full"
              placeholder="mg.mydomain.com"
              value={mailgunDomain}
              onChange={(e) => setMailgunDomain(e.target.value)}
              required
            />
          </label>
        </div>
        <label className="block">
          <span className="text-sm text-slate-300">Mailgun Private API Key</span>
          <input
            type="password"
            className="input mt-1 w-full font-mono text-xs"
            placeholder="key-..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            required
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-300">ملاحظات (اختياري)</span>
          <textarea
            className="input mt-1 w-full"
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
          />
          <span>اجعله النطاق الافتراضي</span>
        </label>
        {err && <p className="text-red-400 text-sm">{err}</p>}
        <button className="btn-primary" disabled={createMut.isPending}>
          {createMut.isPending ? 'جارٍ الإضافة...' : 'إضافة'}
        </button>
      </form>

      <section className="space-y-3">
        <h2 className="font-semibold">النطاقات المسجّلة</h2>
        {!domains?.length && (
          <p className="text-slate-400 text-sm">لا توجد نطاقات بعد.</p>
        )}
        {domains?.map((d) => (
          <div key={d.id} className="card p-4 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold">{d.name}</span>
                {d.is_default && (
                  <span className="text-xs bg-ig-pink/20 text-ig-pink px-2 py-0.5 rounded">
                    افتراضي
                  </span>
                )}
              </div>
              <div className="text-xs text-slate-400 mt-1">Mailgun: {d.mailgun_domain}</div>
              {d.notes && <div className="text-xs text-slate-500 mt-1">{d.notes}</div>}
            </div>
            <button
              className="btn-secondary text-sm"
              onClick={() => {
                if (confirm(`حذف النطاق ${d.name}؟`)) deleteMut.mutate(d.id);
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
