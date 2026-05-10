import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Account, Personality, ProxyType, api } from '../api/client';

const PROXY_LABELS: Record<NonNullable<ProxyType>, { label: string; color: string; dot: string }> = {
  mobile_4g:   { label: '📱 جوال 4G', color: 'bg-green-900/40 text-green-300', dot: 'bg-green-400' },
  residential: { label: '🏠 سكني',     color: 'bg-yellow-900/40 text-yellow-300', dot: 'bg-yellow-400' },
  datacenter:  { label: '🖥 داتاسنتر', color: 'bg-red-900/40 text-red-300', dot: 'bg-red-400' },
};

const SESSION_STYLE_LABELS = {
  active:   { label: 'نشيط',    color: 'text-green-400' },
  moderate: { label: 'متوسط',   color: 'text-blue-400' },
  quiet:    { label: 'هادئ',    color: 'text-slate-400' },
};

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
            onUpdate={() => qc.invalidateQueries({ queryKey: ['accounts'] })}
          />
        ))}
      </div>
    </div>
  );
}

/* ── AccountCard ─────────────────────────────────────────────────────────── */
function AccountCard({
  acc,
  onRun,
  onDelete,
  runPending,
  onUpdate,
}: {
  acc: Account;
  onRun: () => void;
  onDelete: () => void;
  runPending: boolean;
  onUpdate: () => void;
}) {
  const [panel, setPanel] = useState<'none' | 'proxy' | 'personality'>('none');

  const togglePanel = (p: 'proxy' | 'personality') =>
    setPanel((cur) => (cur === p ? 'none' : p));

  const parsedPersonality: Personality = (() => {
    try {
      return acc.personality ? JSON.parse(acc.personality) : { skip_rate: 0.15, session_style: 'moderate', warmup_count: 3 };
    } catch {
      return { skip_rate: 0.15, session_style: 'moderate', warmup_count: 3 };
    }
  })();

  const proxyMeta = acc.proxy_type ? PROXY_LABELS[acc.proxy_type] : null;
  const styleMeta = SESSION_STYLE_LABELS[parsedPersonality.session_style] ?? SESSION_STYLE_LABELS.moderate;

  // Days since account creation
  const ageDays = Math.floor((Date.now() - new Date(acc.created_at).getTime()) / 86_400_000);

  return (
    <div className="card space-y-3">
      {/* ── Header ── */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-lg font-semibold">@{acc.username}</p>
            <span className={`px-2 py-0.5 rounded text-xs ${acc.is_active ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'}`}>
              {acc.is_active ? 'نشط' : 'غير نشط'}
            </span>

            {/* Proxy type badge */}
            {proxyMeta ? (
              <span className={`px-2 py-0.5 rounded text-xs flex items-center gap-1 ${proxyMeta.color}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${proxyMeta.dot}`} />
                {proxyMeta.label}
              </span>
            ) : acc.has_proxy ? (
              <span className="px-2 py-0.5 rounded text-xs bg-blue-900/40 text-blue-300">
                🌐 بروكسي
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-500">
                بدون بروكسي
              </span>
            )}

            {/* Personality badge */}
            <span className={`px-2 py-0.5 rounded text-xs bg-slate-800 ${styleMeta.color}`}>
              {styleMeta.label} · تخطي {Math.round(parsedPersonality.skip_rate * 100)}%
            </span>

            {/* New-account warning */}
            {ageDays < 30 && (
              <span className="px-2 py-0.5 rounded text-xs bg-orange-900/40 text-orange-300">
                حساب جديد ({ageDays} يوم)
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
            الأهداف
          </Link>
          <Link to={`/accounts/${acc.id}/logs`} className="btn-secondary text-sm">
            السجل
          </Link>
          <button
            type="button"
            onClick={() => togglePanel('proxy')}
            className={`btn-secondary text-sm ${panel === 'proxy' ? 'ring-1 ring-blue-500' : ''}`}
          >
            🌐 بروكسي
          </button>
          <button
            type="button"
            onClick={() => togglePanel('personality')}
            className={`btn-secondary text-sm ${panel === 'personality' ? 'ring-1 ring-purple-500' : ''}`}
          >
            🧠 شخصية
          </button>
          <button
            type="button"
            onClick={onRun}
            disabled={runPending}
            className="btn-primary text-sm"
          >
            تشغيل
          </button>
          <button type="button" onClick={onDelete} className="btn-danger text-sm">
            حذف
          </button>
        </div>
      </div>

      {/* ── Proxy panel ── */}
      {panel === 'proxy' && (
        <ProxyPanel acc={acc} onUpdate={onUpdate} />
      )}

      {/* ── Personality panel ── */}
      {panel === 'personality' && (
        <PersonalityPanel acc={acc} current={parsedPersonality} onUpdate={onUpdate} />
      )}
    </div>
  );
}

/* ── ProxyPanel ─────────────────────────────────────────────────────────── */
function ProxyPanel({ acc, onUpdate }: { acc: Account; onUpdate: () => void }) {
  const [proxyInput, setProxyInput] = useState('');
  const [proxyType, setProxyType] = useState<string>(acc.proxy_type ?? 'residential');
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

  const saveProxy = useMutation({
    mutationFn: async (payload: { proxy: string | null; proxy_type: string | null }) =>
      (await api.patch<Account>(`/accounts/${acc.id}/proxy`, payload)).data,
    onSuccess: () => {
      setMsg({ text: 'تم الحفظ.', ok: true });
      onUpdate();
    },
    onError: (err: any) => {
      setMsg({ text: err?.response?.data?.detail ?? 'حدث خطأ', ok: false });
    },
  });

  const proxy = proxyInput.trim() || null;

  return (
    <div className="border-t border-slate-800 pt-4 space-y-3">
      <p className="text-sm font-medium text-slate-300">إعداد البروكسي</p>

      {/* Proxy type selector */}
      <div className="space-y-1">
        <p className="text-xs text-slate-400">نوع البروكسي:</p>
        <div className="flex gap-2 flex-wrap">
          {(['mobile_4g', 'residential', 'datacenter'] as const).map((t) => {
            const meta = PROXY_LABELS[t];
            return (
              <button
                key={t}
                type="button"
                onClick={() => setProxyType(t)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                  proxyType === t
                    ? 'border-ig-pink bg-ig-pink/10 text-white'
                    : 'border-slate-700 text-slate-400 hover:border-slate-600'
                }`}
              >
                {meta.label}
              </button>
            );
          })}
        </div>
        {proxyType === 'datacenter' && (
          <p className="text-xs text-red-400">⚠️ بروكسي الداتاسنتر خطر جداً — نسبة الكشف مرتفعة</p>
        )}
        {proxyType === 'residential' && (
          <p className="text-xs text-yellow-400">⚠️ البروكسي السكني مخاطرة متوسطة — يُفضَّل الجوال</p>
        )}
        {proxyType === 'mobile_4g' && (
          <p className="text-xs text-green-400">✓ بروكسي الجوال — الأفضل لتجنب الكشف</p>
        )}
      </div>

      <div className="text-xs text-slate-500 font-mono bg-slate-900 rounded px-3 py-2 space-y-0.5">
        <p>http://user:pass@host:port</p>
        <p>socks5://user:pass@host:port</p>
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
          onClick={() => saveProxy.mutate({ proxy, proxy_type: proxy ? proxyType : null })}
          disabled={saveProxy.isPending}
        >
          {saveProxy.isPending ? '...' : 'حفظ'}
        </button>
        {acc.has_proxy && (
          <button
            type="button"
            className="btn-danger text-sm"
            onClick={() => { setProxyInput(''); saveProxy.mutate({ proxy: null, proxy_type: null }); }}
            disabled={saveProxy.isPending}
          >
            حذف
          </button>
        )}
      </div>

      {msg && (
        <p className={`text-xs ${msg.ok ? 'text-green-400' : 'text-red-400'}`}>{msg.text}</p>
      )}
    </div>
  );
}

/* ── PersonalityPanel ───────────────────────────────────────────────────── */
function PersonalityPanel({
  acc,
  current,
  onUpdate,
}: {
  acc: Account;
  current: Personality;
  onUpdate: () => void;
}) {
  const [form, setForm] = useState<Personality>({ ...current });
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

  const save = useMutation({
    mutationFn: async () =>
      (await api.patch<Account>(`/accounts/${acc.id}/personality`, form)).data,
    onSuccess: () => {
      setMsg({ text: 'تم حفظ الشخصية.', ok: true });
      onUpdate();
    },
    onError: () => setMsg({ text: 'حدث خطأ', ok: false }),
  });

  const styles: Array<{ key: Personality['session_style']; label: string; desc: string }> = [
    { key: 'active',   label: 'نشيط',   desc: 'تأخير أقصر — نشاط أكثر' },
    { key: 'moderate', label: 'متوسط',  desc: 'متوازن — الافتراضي' },
    { key: 'quiet',    label: 'هادئ',   desc: 'تأخير أطول — أكثر أماناً' },
  ];

  return (
    <div className="border-t border-slate-800 pt-4 space-y-4">
      <p className="text-sm font-medium text-slate-300">شخصية الحساب</p>
      <p className="text-xs text-slate-500">
        كل حساب له سلوك مختلف — يُربك أنظمة الكشف التي تحاول تجميع الأنماط
      </p>

      {/* Session style */}
      <div className="space-y-2">
        <p className="text-xs text-slate-400">أسلوب الجلسة:</p>
        <div className="grid grid-cols-3 gap-2">
          {styles.map(({ key, label, desc }) => (
            <button
              key={key}
              type="button"
              onClick={() => setForm({ ...form, session_style: key })}
              className={`text-xs px-3 py-2.5 rounded-lg border transition-colors text-right space-y-0.5 ${
                form.session_style === key
                  ? 'border-ig-pink bg-ig-pink/10'
                  : 'border-slate-700 hover:border-slate-600'
              }`}
            >
              <p className="font-medium">{label}</p>
              <p className="text-slate-500">{desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Skip rate */}
      <div className="space-y-2">
        <div className="flex justify-between">
          <p className="text-xs text-slate-400">نسبة التخطي العشوائي:</p>
          <p className="text-xs text-slate-300 font-mono">{Math.round(form.skip_rate * 100)}%</p>
        </div>
        <input
          type="range"
          min={5}
          max={35}
          step={1}
          value={Math.round(form.skip_rate * 100)}
          onChange={(e) => setForm({ ...form, skip_rate: parseInt(e.target.value) / 100 })}
          className="w-full accent-ig-pink"
        />
        <div className="flex justify-between text-xs text-slate-600">
          <span>5% (أكثر نشاطاً)</span>
          <span>35% (أكثر بشرية)</span>
        </div>
      </div>

      {/* Warmup count */}
      <div className="space-y-1">
        <p className="text-xs text-slate-400">عدد إجراءات الـ Warm-up:</p>
        <div className="flex gap-2">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setForm({ ...form, warmup_count: n })}
              className={`w-9 h-9 rounded-lg text-sm border transition-colors ${
                form.warmup_count === n
                  ? 'border-ig-pink bg-ig-pink/10 text-white'
                  : 'border-slate-700 text-slate-400 hover:border-slate-600'
              }`}
            >
              {n}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-600">
          إجراءات عشوائية (تصفح الفيد / الاستكشاف / الملف / الرسائل / الريلز) قبل البدء بالإعجابات
        </p>
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          className="btn-primary text-sm"
          onClick={() => save.mutate()}
          disabled={save.isPending}
        >
          {save.isPending ? 'جارٍ الحفظ...' : 'حفظ الشخصية'}
        </button>
      </div>

      {msg && (
        <p className={`text-xs ${msg.ok ? 'text-green-400' : 'text-red-400'}`}>{msg.text}</p>
      )}
    </div>
  );
}
