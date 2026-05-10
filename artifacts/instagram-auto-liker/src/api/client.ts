import axios, { AxiosError } from 'axios';

const TOKEN_KEY = 'ial-token';

export const api = axios.create({
  baseURL: '/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => {
    if (err.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  },
);

export const auth = {
  login: async (username: string, password: string) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const { data } = await axios.post<{ access_token: string }>('/api/auth/login', params);
    localStorage.setItem(TOKEN_KEY, data.access_token);
    return data;
  },
  logout: () => localStorage.removeItem(TOKEN_KEY),
  isAuthed: () => Boolean(localStorage.getItem(TOKEN_KEY)),
};

export type ProxyType = 'residential' | 'mobile_4g' | 'datacenter' | null;

export type Account = {
  id: number;
  username: string;
  is_active: boolean;
  has_proxy: boolean;
  has_totp: boolean;
  proxy_type: ProxyType;
  personality: string | null;
  last_login_at: string | null;
  last_error: string | null;
  session_renewed_at: string | null;
  created_at: string;
};

export type Personality = {
  skip_rate: number;       // 0.05 – 0.35
  session_style: 'active' | 'moderate' | 'quiet';
  warmup_count: number;    // 1 – 5
};

export type Target = {
  id: number;
  account_id: number;
  username: string;
  likes_per_run: number;
  is_enabled: boolean;
  comment_enabled: boolean;
  comment_templates: string[];
  story_watch_enabled: boolean;
  created_at: string;
};

export type Run = {
  id: number;
  account_id: number;
  status: string;
  triggered_by: string;
  likes_attempted: number;
  likes_succeeded: number;
  likes_skipped: number;
  likes_failed: number;
  started_at: string;
  finished_at: string | null;
  error: string | null;
};

export type LikeLog = {
  id: number;
  run_id: number | null;
  account_id: number;
  target_username: string;
  media_id: string;
  media_url: string | null;
  success: boolean;
  skipped_reason: string | null;
  error: string | null;
  created_at: string;
};

export type ScheduleSettings = {
  enabled: boolean;
  interval_hours: number;
  daily_like_limit: number;
  hourly_like_limit: number;
  min_delay_seconds: number;
  max_delay_seconds: number;
  warmup_enabled: boolean;
  active_hours_start: number;
  active_hours_end: number;
  new_account_mode: boolean;
};

export type StatsOverview = {
  total_7d: number;
  today_likes: number;
  success_rate: number;
  accounts_active: number;
  by_day: { date: string; likes: number }[];
  by_account: { username: string; likes: number }[];
};
