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
        comment_enabled: false,
        comment_templates: [],
        story_watch_enabled: false,
      })).data,
    onSuccess: () => {
      setUsername('');
      qc.invalidateQueries({ queryKey: ['targets', accountId] });
    },
  });

  const update = useMutation({
    mutationFn: async (payload: { id: number; data: Partial<Target> }) =>
      (await api.patch<Target>(`/accounts/${accountId}/targets/${payload.id}`, payload.data)).data,
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

      {/* Add target form */}
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

      {/* Targets list */}
      <div className="space-y-4">
        {targets.length === 0 && !isLoading && (
          <div className="card text-center py-8 text-slate-400">لا توجد حسابات مستهدفة بعد.</div>
        )}

        {targets.map((t) => (
          <TargetCard
            key={t.id}
            target={t}
            onUpdate={(data) => update.mutate({ id: t.id, data })}
            onDelete={() => {
              if (confirm(`حذف @${t.username}؟`)) remove.mutate(t.id);
            }}
            isPending={update.isPending}
          />
        ))}
      </div>
    </div>
  );
}

function TargetCard({
  target,
  onUpdate,
  onDelete,
  isPending,
}: {
  target: Target;
  onUpdate: (data: Partial<Target>) => void;
  onDelete: () => void;
  isPending: boolean;
}) {
  const [editingComments, setEditingComments] = useState(false);
  const [commentsText, setCommentsText] = useState(
    target.comment_templates.join('\n')
  );

  const saveComments = () => {
    const templates = commentsText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);
    onUpdate({ comment_templates: templates });
    setEditingComments(false);
  };

  return (
    <div className="card space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="text-lg font-semibold">@{target.username}</p>
          <p className="text-xs text-slate-500">إعجابات لكل تشغيل: {target.likes_per_run}</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            type="button"
            className="btn-secondary text-xs"
            onClick={() => onUpdate({ is_enabled: !target.is_enabled })}
            disabled={isPending}
          >
            {target.is_enabled ? 'تعطيل' : 'تفعيل'}
          </button>
          <button
            type="button"
            className="btn-danger text-xs"
            onClick={onDelete}
          >
            حذف
          </button>
        </div>
      </div>

      {/* Status badge */}
      <span
        className={`inline-block px-2 py-0.5 rounded text-xs ${
          target.is_enabled
            ? 'bg-green-900/40 text-green-300'
            : 'bg-slate-800 text-slate-400'
        }`}
      >
        {target.is_enabled ? 'مفعّل' : 'معطّل'}
      </span>

      {/* Feature toggles */}
      <div className="border-t border-slate-800 pt-4 grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Story watch */}
        <label className="flex items-center gap-3 cursor-pointer select-none">
          <div
            onClick={() => onUpdate({ story_watch_enabled: !target.story_watch_enabled })}
            className={`w-10 h-6 rounded-full transition-colors flex items-center px-1 cursor-pointer ${
              target.story_watch_enabled ? 'bg-ig-pink' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full bg-white transition-transform ${
                target.story_watch_enabled ? 'translate-x-4' : 'translate-x-0'
              }`}
            />
          </div>
          <div>
            <p className="text-sm font-medium">مشاهدة الستوري</p>
            <p className="text-xs text-slate-500">يشاهد الستوري تلقائياً في كل تشغيل</p>
          </div>
        </label>

        {/* Comment toggle */}
        <label className="flex items-center gap-3 cursor-pointer select-none">
          <div
            onClick={() => onUpdate({ comment_enabled: !target.comment_enabled })}
            className={`w-10 h-6 rounded-full transition-colors flex items-center px-1 cursor-pointer ${
              target.comment_enabled ? 'bg-ig-pink' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full bg-white transition-transform ${
                target.comment_enabled ? 'translate-x-4' : 'translate-x-0'
              }`}
            />
          </div>
          <div>
            <p className="text-sm font-medium">التعليق التلقائي</p>
            <p className="text-xs text-slate-500">يعلّق بعشوائية من قائمتك</p>
          </div>
        </label>
      </div>

      {/* Comment templates editor */}
      {target.comment_enabled && (
        <div className="border-t border-slate-800 pt-4 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-300">
              قائمة التعليقات
              <span className="text-slate-500 mr-2 text-xs">
                ({target.comment_templates.length} تعليق)
              </span>
            </p>
            {!editingComments && (
              <button
                type="button"
                className="btn-secondary text-xs"
                onClick={() => {
                  setCommentsText(target.comment_templates.join('\n'));
                  setEditingComments(true);
                }}
              >
                تعديل
              </button>
            )}
          </div>

          {editingComments ? (
            <div className="space-y-2">
              <textarea
                className="input h-36 text-sm font-mono"
                value={commentsText}
                onChange={(e) => setCommentsText(e.target.value)}
                placeholder={'تعليق رائع!\nمنشور جميل 🔥\nاستمر هكذا!'}
              />
              <p className="text-xs text-slate-500">تعليق واحد في كل سطر. سيُختار واحد عشوائياً.</p>
              <div className="flex gap-2">
                <button type="button" className="btn-primary text-sm" onClick={saveComments}>
                  حفظ
                </button>
                <button
                  type="button"
                  className="btn-secondary text-sm"
                  onClick={() => setEditingComments(false)}
                >
                  إلغاء
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              {target.comment_templates.length === 0 ? (
                <p className="text-xs text-yellow-400">
                  ⚠️ لم تُضف تعليقات بعد — اضغط "تعديل" لإضافتها.
                </p>
              ) : (
                target.comment_templates.map((c, i) => (
                  <p key={i} className="text-xs text-slate-400 bg-slate-800 px-3 py-1 rounded">
                    {c}
                  </p>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
