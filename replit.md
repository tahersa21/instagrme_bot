# Instagram Auto Liker

A self-hosted dashboard for automatically liking Instagram posts from target accounts, with rate limiting and scheduling.

## Run & Operate

- **Frontend** (`artifacts/instagram-auto-liker: web`): React + Vite on port 18962, preview at `/`
- **Backend** (`artifacts/api-server: API Server`): Python FastAPI (uvicorn) on port 8080, serves `/api`
- Login credentials: **admin / admin123** (configurable via `ADMIN_USERNAME` / `ADMIN_PASSWORD` env vars)

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- **Frontend**: React 19, Vite 7, Tailwind CSS v4, React Router v6, TanStack Query, Axios
- **Backend**: Python 3.11, FastAPI, SQLAlchemy + PostgreSQL, APScheduler, instagrapi, python-jose, Fernet encryption
- **Auth**: JWT bearer tokens (dashboard login), Fernet symmetric encryption for Instagram session storage

## Where things live

- `artifacts/instagram-auto-liker/src/` — React frontend source
  - `api/client.ts` — axios instance + auth helpers + type definitions
  - `pages/` — Login, Dashboard, IgLogin, Targets, Schedule, Logs, Analytics
  - `components/Layout.tsx` — sidebar + nav
- `instagram-auto-liker/backend/app/` — FastAPI backend
  - `main.py` — app factory, CORS, router registration
  - `routers/` — accounts, targets, runs, logs, settings, auth, stats
  - `services/` — ig_client, liker, scheduler, crypto, auth
  - `models/` — SQLAlchemy ORM: Account, Target, Run, LikeLog, SettingsKV
- `artifacts/api-server/.replit-artifact/artifact.toml` — runs uvicorn for the Python backend

## Architecture decisions

- The Node.js `api-server` artifact was repurposed to run the Python FastAPI backend via its workflow run command.
- All Instagram session data (cookies, passwords) is Fernet-encrypted before DB storage using `MASTER_KEY`.
- Dashboard auth uses a separate JWT with `JWT_SECRET`; Instagram auth is handled by instagrapi.
- The PostgreSQL `DATABASE_URL` env var is used automatically by SQLAlchemy (psycopg2-binary driver).
- APScheduler runs inside the FastAPI process for background like jobs.

## Product

Users log in to the dashboard (admin/admin123), connect their Instagram accounts (by password or session cookies), set target accounts to like posts from, configure rate limits and schedules, and trigger manual or automatic like runs.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- The Python backend must run from `/home/runner/workspace/instagram-auto-liker/backend` — absolute path required in the artifact.toml run command.
- `MASTER_KEY` and `JWT_SECRET` must stay stable — changing them invalidates all stored encrypted sessions.
- `DATABASE_URL` is taken from the Replit environment (PostgreSQL); SQLite is NOT used despite the .env default.
- Tailwind v4 in use — cannot use `@apply` with custom component class names (e.g. `.btn`). Define styles with plain CSS properties instead.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
