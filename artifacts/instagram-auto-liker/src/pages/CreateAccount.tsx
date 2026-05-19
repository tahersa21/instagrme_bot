import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  api,
  type AccountCreationJob,
  type Domain,
  type SmsProvider,
} from '../api/client';

const statusLabels: Record<AccountCreationJob['status'], string> = {
  pending: 'في الانتظار',
  running: 'جارٍ التنفيذ',
  email_otp_wait: 'انتظار رمز البريد',
  phone_otp_wait: 'انتظار رمز الهاتف',
  success: 'نجح',
  failed: 'فشل',
};

const statusColors: Record<AccountCreationJob['status'], string> = {
  pending: 'bg-slate-700 text-slate-200',
  running: 'bg-blue-600/30 text-blue-300',
  email_otp_wait: 'bg-yellow-600/30 text-yellow-300',
  phone_otp_wait: 'bg-yellow-600/30 text-yellow-300',
  success: 'bg-green-600/30 text-green-300',
  failed: 'bg-red-600/30 text-red-300',
};

export default function CreateAccount() {
  const qc = useQueryClient();
  const { data: domains } = useQuery({
    queryKey: ['domains'],
    queryFn: async () => (await api.get<Domain[]>('/domains')).data,
  });
  const { data: providers } = useQuery({
    queryKey: ['sms-providers'],
    queryFn: async () => (await api.get<SmsProvider[]>('/sms-providers')).data,
  });
  const { data: jobs } = useQuery({
    queryKey: ['account-creation-jobs'],
    queryFn: async () =>
      (await api.get<AccountCreationJob[]>('/account-creation')).data,
    refetchInterval: 5000,
  });

  const [domainId, setDomainId] = useState<string>('');
  const [smsId, setSmsId] = useState<string>('');
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [emailLocal, setEmailLocal] = useState('');
  const [password, setPassword] = useState('');
  const [proxy, setProxy] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        domain_id: Number(domainId),
      };
      if (smsId) payload.sms_provider_id = Number(smsId);
      if (fullName) payload.full_name = fullName;
      if (username) payload.username = username;
      if (emailLocal) payload.email_local_part = emailLocal;
      if (password) payload.password = password;
      if (proxy) payload.proxy = proxy;
      const { data } = await api.post<AccountCreationJob>('/account-creation', payload);
      return data;
    },
    onSuccess: (j) => {
      qc.invalidateQueries({ queryKey: ['account-creation-jobs'] });
      setSelectedJobId(j.id);
      setErr(null);
    },
    onError: (e: unknown) => {
      const msg =
        (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
        'فشل بدء الإنشاء';
      setErr(msg);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: number) => api.delete(`/account-creation/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['account-creation-jobs'] }),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!domainId) {
      setErr('اختر نطاقاً أولاً');
      return;
    }
    createMut.mutate();
  };

  const selectedJob = jobs?.find((j) => j.id === selectedJobId);

  return (
    <div className="space-y-8 max-w-6xl">
      <header>
        <h1 className="text-2xl font-bold mb-1">إنشاء حساب Instagram تلقائياً</h1>
        <p className="text-sm text-slate-400">
          تنبيه: هذا يخالف شروط استخدام Instagram. نسبة النجاح منخفضة (&lt;30%) وقد تُحظر الحسابات
          أو IP. استخدم بروكسي residential وحساب Mailgun فعّال.
        </p>
      </header>

      {(!domains?.length || !providers?.length) && (
        <div className="card p-4 bg-yellow-900/20 border-yellow-700/40 text-yellow-200 text-sm">
          {!domains?.length && <div>أضف نطاقاً واحداً على الأقل من صفحة "النطاقات" أولاً.</div>}
          {!providers?.length && (
            <div>يُنصح بإضافة مزوّد SMS من صفحة "مزوّدو SMS" قبل البدء.</div>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        <form onSubmit={onSubmit} className="card p-6 space-y-4">
          <h2 className="font-semibold">بيانات الحساب الجديد</h2>

          <label className="block">
            <span className="text-sm text-slate-300">النطاق *</span>
            <select
              className="input mt-1 w-full"
              value={domainId}
              onChange={(e) => setDomainId(e.target.value)}
              required
            >
              <option value="">— اختر —</option>
              {domains?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} {d.is_default ? '(افتراضي)' : ''}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-sm text-slate-300">مزوّد SMS (اختياري)</span>
            <select
              className="input mt-1 w-full"
              value={smsId}
              onChange={(e) => setSmsId(e.target.value)}
            >
              <option value="">— بدون (سيفشل إن طلب Instagram هاتفاً) —</option>
              {providers?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.provider_type})
                </option>
              ))}
            </select>
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-sm text-slate-300">الاسم الكامل</span>
              <input
                className="input mt-1 w-full"
                placeholder="(تلقائي)"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </label>
            <label className="block">
              <span className="text-sm text-slate-300">اسم المستخدم</span>
              <input
                className="input mt-1 w-full"
                placeholder="(تلقائي)"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
          </div>

          <label className="block">
            <span className="text-sm text-slate-300">
              البريد (الجزء قبل @{domains?.find((d) => String(d.id) === domainId)?.name ?? 'domain'})
            </span>
            <input
              className="input mt-1 w-full"
              placeholder="(تلقائي)"
              value={emailLocal}
              onChange={(e) => setEmailLocal(e.target.value)}
            />
          </label>

          <label className="block">
            <span className="text-sm text-slate-300">كلمة المرور</span>
            <input
              className="input mt-1 w-full font-mono text-xs"
              placeholder="(تلقائي - 14 حرفاً عشوائياً)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>

          <label className="block">
            <span className="text-sm text-slate-300">بروكسي (موصى به بشدة)</span>
            <input
              className="input mt-1 w-full font-mono text-xs"
              placeholder="http://user:pass@host:port"
              value={proxy}
              onChange={(e) => setProxy(e.target.value)}
            />
          </label>

          {err && <p className="text-red-400 text-sm">{err}</p>}
          <button className="btn-primary w-full" disabled={createMut.isPending}>
            {createMut.isPending ? 'جارٍ البدء...' : 'ابدأ الإنشاء'}
          </button>
        </form>

        <div className="space-y-3">
          <h2 className="font-semibold">المهام الأخيرة</h2>
          {!jobs?.length && (
            <p className="text-slate-400 text-sm">لا توجد مهام بعد.</p>
          )}
          <div className="space-y-2 max-h-[600px] overflow-auto">
            {jobs?.map((j) => (
              <div
                key={j.id}
                className={`card p-3 cursor-pointer ${
                  selectedJobId === j.id ? 'ring-2 ring-ig-pink' : ''
                }`}
                onClick={() => setSelectedJobId(j.id)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-mono text-sm">{j.username}</div>
                    <div className="text-xs text-slate-500">{j.email}</div>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded ${statusColors[j.status]}`}>
                    {statusLabels[j.status]}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {selectedJob && (
        <section className="card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">تفاصيل المهمة #{selectedJob.id}</h2>
            <button
              className="btn-secondary text-sm"
              onClick={() => {
                if (confirm('حذف هذه المهمة من السجل؟')) deleteMut.mutate(selectedJob.id);
              }}
            >
              حذف
            </button>
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-slate-400">الحالة</div>
              <div>{statusLabels[selectedJob.status]}</div>
            </div>
            <div>
              <div className="text-slate-400">الهاتف</div>
              <div className="font-mono">{selectedJob.phone_number ?? '—'}</div>
            </div>
            <div>
              <div className="text-slate-400">حساب مُنشأ</div>
              <div>{selectedJob.created_account_id ?? '—'}</div>
            </div>
          </div>
          {selectedJob.error && (
            <div className="bg-red-900/20 border border-red-700/40 p-3 rounded text-red-300 text-sm">
              {selectedJob.error}
            </div>
          )}
          <div>
            <h3 className="text-sm font-semibold mb-2">السجل</h3>
            <div className="bg-slate-950 border border-slate-800 rounded p-3 max-h-72 overflow-auto font-mono text-xs space-y-1">
              {selectedJob.logs.length === 0 && (
                <div className="text-slate-500">لا توجد إدخالات بعد...</div>
              )}
              {selectedJob.logs.map((log, i) => (
                <div key={i} className="text-slate-300">
                  <span className="text-slate-500">[{log.ts.slice(11, 19)}]</span> {log.msg}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
