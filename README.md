# QueueLess – Virtual Queue & Appointment Management

QueueLess lets banks, salons, clinics, government offices and service centers manage customer queues digitally. Implemented so far: authentication, business/staff/service management (Phase 1) and the complete queue engine, staff counter console, appointments, notifications, analytics and live updates (Phase 2).

| Layer    | Stack |
|----------|-------|
| Backend  | Python 3.11, FastAPI, SQLAlchemy 2, Pydantic 2, PyJWT, bcrypt |
| Frontend | React 18, Vite, Material UI 6, React Router 6, Axios |
| Database | SQLite (default) – PostgreSQL via `DATABASE_URL` |
| Tests    | Pytest (backend), Vitest + Testing Library (frontend) |

---

## Quick start (Windows PowerShell)

### 1. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env          # then set SECRET_KEY (see below)
uvicorn app.main:app --reload
```

- API: http://localhost:8000/api/v1
- Interactive docs (Swagger): http://localhost:8000/docs (ReDoc at `/redoc`)
- Tables are created automatically on startup.
- **Upgrading from Phase 1:** Phase 2 added columns. Stop the backend, delete `backend\queueless.db`, and start it again. The app refuses to start against an outdated schema and tells you which columns are missing.

Generate a secret key and paste it into `backend/.env`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Create a super admin (there is no public sign-up for this role):

```powershell
python -m app.cli create-superadmin --email admin@example.com --name "Platform Admin"
```

### 2. Frontend (second PowerShell window)

```powershell
cd frontend
npm install
Copy-Item .env.example .env          # optional; defaults to http://localhost:8000/api/v1
npm run dev
```

Open http://localhost:5173.

### Running both together

Use two terminals: one runs `uvicorn app.main:app --reload` inside `backend` (with the venv activated), the other runs `npm run dev` inside `frontend`. The backend allows CORS from `http://localhost:5173` by default (`CORS_ORIGINS`).

### Tests

```powershell
# backend (venv active)
cd backend
pytest -q

# frontend
cd frontend
npm test
```

---

## Environment variables

`backend/.env`

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./queueless.db` | SQLAlchemy URL. PostgreSQL: `postgresql+psycopg://user:pass@localhost:5432/queueless` (`pip install "psycopg[binary]"`) |
| `SECRET_KEY` | — (required, ≥ 32 chars) | JWT signing key |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh session lifetime |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | `30` | Reset link lifetime |
| `BCRYPT_ROUNDS` | `12` | Password hashing cost |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated |
| `FRONTEND_URL` | `http://localhost:5173` | Used to build password reset links |
| `DEBUG` | `false` | Verbose logging |

`frontend/.env`

| Variable | Default |
|----------|---------|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` |

---

## Architecture

```
backend/app/
  main.py            app factory: middleware, CORS, error handlers, routers
  config.py          typed settings from environment / .env
  database.py        engine, session, Base (naming conventions for portable constraints)
  cli.py             admin commands (create-superadmin)
  models/            SQLAlchemy models (one file per aggregate)
  schemas/           Pydantic request/response models
  routers/           thin HTTP layer – parse input, call a service, return a schema
  services/          business logic, authorization and transactions
  core/              security (JWT, bcrypt), dependencies, exceptions
  middleware/        request id, client IP (for audit logs), timing logs
  websocket/         connection manager + authenticated business channel
backend/tests/       pytest suite (in-memory SQLite per test)

frontend/src/
  services/          Axios client (auto refresh) + one module per API area
  context/           AuthContext, SnackbarContext
  hooks/             useAuth, useAsync, useBusinessAccess, useDebounced, useSnackbar
  layouts/           AuthLayout, DashboardLayout (role-based navigation)
  components/        shared UI, form components, business/service panels
  pages/             auth, customer, owner, staff, admin, business management
  theme/ utils/
```

**Request flow:** router → service function → SQLAlchemy session → commit. Services raise typed errors (`NotFoundError`, `PermissionDeniedError`, `ConflictError`, …) that are converted to JSON responses `{ "detail": "...", "code": "..." }`.

**Roles.** A user has one *platform role* (`SUPER_ADMIN`, `BUSINESS_OWNER`, `STAFF`, `CUSTOMER`) that decides their dashboard, plus a *business role* per business in `business_members` (`OWNER`, `MANAGER`, `STAFF`):

| Action | Business STAFF | MANAGER | OWNER | SUPER_ADMIN |
|--------|:-:|:-:|:-:|:-:|
| View business stats, members, services (incl. inactive), counters | ✓ | ✓ | ✓ | ✓ |
| Edit profile / working hours, manage services & counters | | ✓ | ✓ | ✓ |
| Add / change / remove members, activate / deactivate business | | | ✓ | ✓ |

**Tenant isolation.** Every private endpoint resolves the caller's membership from the database (`services/access_control.py`). A business id in the URL is never trusted on its own, and child records (members, services, counters) are always looked up together with their owning business, so ids from another business return 403/404.

**Authentication.** Short-lived JWT access tokens plus refresh tokens. Each login creates a row in `refresh_tokens` (only the token id is stored). Refreshing rotates the token; replaying an already-used refresh token revokes all of that user's sessions. Access tokens carry their session id, so logout, password changes and account deactivation take effect immediately.

---

## API (prefix `/api/v1`)

Full interactive documentation: http://localhost:8000/docs. Roles: *STAFF+* = any member of the business, *MANAGER+* = managers and owners (super admins pass every business check). A *counter operator* is a manager/owner of the business, or the staff member assigned to that counter.

**Auth & users**

| Endpoint | Access |
|---|---|
| `POST /auth/register/customer`, `POST /auth/register/business-owner`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` | public |
| `GET /auth/me`, `PATCH /users/me`, `POST /users/me/change-password` | signed in |
| `POST /auth/forgot-password`, `POST /auth/reset-password` | public |

**Businesses, members, services**

| Endpoint | Access |
|---|---|
| `GET /businesses`, `GET /businesses/{id}` | public (active only) |
| `POST /businesses` | BUSINESS_OWNER, SUPER_ADMIN |
| `GET /businesses/mine` | signed in |
| `PATCH /businesses/{id}`, `PUT /businesses/{id}/working-hours` | MANAGER+ |
| `PATCH /businesses/{id}/status` | OWNER |
| `GET /businesses/{id}/stats` | STAFF+ |
| `GET /businesses/{id}/analytics?days=7` | MANAGER+ |
| `GET/POST /businesses/{id}/members`, `PATCH/DELETE /businesses/{id}/members/{member_id}` | read STAFF+, write OWNER |
| `GET /businesses/{id}/services`, `GET /services/{id}` | public (active only) |
| `POST /businesses/{id}/services`, `PATCH/DELETE /services/{id}` | MANAGER+ |
| `GET /services/{id}/stats` | STAFF+ |

**Queues and tokens**

| Endpoint | Access |
|---|---|
| `GET /queues?business_id=&service_id=` | public: today's open/paused queues |
| `GET /queues/{id}` | public summary (counts and codes only, no customer data) |
| `POST /queues` `{service_id, max_capacity}` | MANAGER+: open (or reopen) today's queue |
| `PATCH /queues/{id}` `{max_capacity}`; `POST /queues/{id}/pause`, `/resume`, `/close` | MANAGER+ |
| `POST /queues/{id}/join` | signed in: returns the token with position and estimate |
| `POST /queues/{id}/walk-ins` `{guest_name, guest_phone}` | STAFF+ |
| `GET /queues/{id}/tokens` | STAFF+ (includes contact details) |
| `GET /businesses/{id}/queues` | STAFF+: current and previous sessions |
| `GET /tokens` (my history), `GET /tokens/{id}` | token owner, or STAFF+ |
| `POST /tokens/{id}/cancel` | the customer, or a counter operator |
| `POST /tokens/{id}/call` `{counter_id}`, `/recall`, `/start`, `/complete`, `/skip`, `/no-show` | counter operator |

**Counters**

| Endpoint | Access |
|---|---|
| `GET /businesses/{id}/counters`, `GET /services/{id}/counters`, `GET /counters/{id}` | STAFF+ |
| `GET /counters/assigned` | signed in: counters assigned to me |
| `GET /counters/{id}/console` | STAFF+: current token, waiting, skipped, recently completed |
| `POST /counters/{id}/call-next` | counter operator |
| `POST /services/{id}/counters`, `PATCH/DELETE /counters/{id}` (assign staff, move service, online/offline) | MANAGER+ |

**Appointments**

| Endpoint | Access |
|---|---|
| `GET /services/{id}/appointment-slots?date=YYYY-MM-DD` | public |
| `POST /appointments` `{service_id, scheduled_start, notes}` | signed in |
| `GET /appointments` (mine), `GET /appointments/{id}` | the customer, or STAFF+ |
| `POST /appointments/{id}/cancel` | the customer (before start), or MANAGER+ |
| `POST /appointments/{id}/confirm` | MANAGER+ |
| `POST /appointments/{id}/check-in`, `/complete`, `/no-show` | STAFF+ |
| `GET /businesses/{id}/appointments?date=&service_id=&status=` | STAFF+ |

**Notifications, admin, live updates**

| Endpoint | Access |
|---|---|
| `GET /notifications`, `GET /notifications/unread-count`, `PATCH /notifications/{id}/read`, `POST /notifications/read-all` | signed in |
| `GET /admin/stats`, `/admin/users`, `PATCH /admin/users/{id}/status`, `/admin/businesses`, `/admin/audit-logs` | SUPER_ADMIN |
| `WS /ws/queues/{id}` | public; announces changes by queue id only |
| `WS /ws/businesses/{id}?token=<access token>` | business members |

## Queue engine

**Sessions.** A queue session is one service's queue for one local day, in the business's timezone; `(service_id, session_date)` is unique. States: `OPEN`, `PAUSED`, `CLOSED`. Pausing stops new joins *and* calling, so a paused queue shows no estimate. Closing cancels tokens that were still waiting or skipped and notifies those customers. Reopening on the same day continues the numbering. Sessions left open from a previous day are closed when the next day's queue opens.

**Token allocation (concurrency).** `queue_service.allocate_token`:

1. Pre-checks (queue open, today, service available, not full, no duplicate) return friendly errors without locking.
2. One atomic statement, `UPDATE queue_sessions SET next_token_number = next_token_number + 1 WHERE id = ? AND status = 'OPEN' RETURNING next_token_number`, reserves the number *and* takes the session's write lock (a row lock on PostgreSQL, the database write lock on SQLite). Concurrent joins to the same queue are serialized from here on.
3. Capacity and duplicate checks are repeated under the lock, then the token is inserted and committed. Any failure rolls back, which also releases the number.

Database constraints back this up: `UNIQUE(queue_session_id, token_number)`, and a partial unique index that allows only one active token (`WAITING/CALLED/SERVING/SKIPPED`) per customer per session. Token codes are a configurable per-service prefix plus 3 digits, e.g. `A027`.

**Token lifecycle.**

| From | Action | To |
|---|---|---|
| WAITING | call / call-next | CALLED |
| WAITING | cancel | CANCELLED |
| CALLED | start | SERVING |
| CALLED | recall (re-announce) | CALLED |
| CALLED | skip | SKIPPED |
| CALLED | no-show | NO_SHOW |
| SKIPPED | recall | CALLED |
| SKIPPED | no-show / cancel | NO_SHOW / CANCELLED |
| SERVING | complete | COMPLETED |

COMPLETED, CANCELLED and NO_SHOW are final. Every transition is a compare-and-set `UPDATE ... WHERE id = ? AND status IN (allowed)`, so when two staff members act on the same token at once, exactly one succeeds and the other gets a 409 with a clear message. A partial unique index on `queue_tokens(counter_id)` for CALLED/SERVING tokens guarantees that a counter handles one token at a time. `call-next` uses the same compare-and-set and moves on to the next candidate if another counter claimed it first. Every transition is written to `audit_logs` (from/to status, counter), and timestamps are kept for joined, called, started, completed, skipped, no-show and cancelled.

**Counter status** (`AVAILABLE` / `BUSY` / `OFFLINE`) is derived on every read from `is_active` and the token currently at the counter, so it cannot drift out of sync. A busy counter cannot be taken offline, moved or deleted.

**Waiting-time estimate** (`services/wait_time.py`). The service is modelled as *N* active counters, each taking the *average service time* per customer. That average is the mean of real completed services over the last 30 days once there are at least 5 of them, and the configured duration otherwise (`basis` in the response says which). If a counter is free for this customer, the wait is 0. Otherwise it is the time until the first desk frees up (half a service when desks are busy) plus one service per further round of people ahead. No estimate is given when the queue is paused or closed, or when no counters are active. The UI always labels it as an estimate.

**Appointments.** Slots are generated from the service's booking hours (or else its operating hours, or else the business hours) in the business's timezone. Each service sets the appointment length, bookings per slot and an optional bookings-per-day limit. Bookings for one service are serialized by an atomic `UPDATE services SET booking_version = booking_version + 1`, and slot and daily capacity are checked under that lock. A partial unique index blocks duplicate live bookings by the same customer, and an overlap check blocks overlapping bookings across services. Lifecycle: BOOKED, CONFIRMED, CHECKED_IN, COMPLETED, plus CANCELLED (customer before the start, or a manager) and NO_SHOW (after the start). Appointments are separate from walk-in tokens; staff see today's appointments for their service in the counter console.

**Notifications** (in-app only) are created for: joining (token confirmation), approaching turn (top 2 in line, sent once), being called, being skipped, staff cancellations, queue closure, and appointment booked, confirmed or cancelled. Email and SMS are not configured.

**Live updates.** After each change, the API broadcasts `{"event": "queue_updated", "data": {"queue_id": ...}}` on the queue and business channels. Clients re-fetch through the authenticated REST API, so no customer data travels over the public socket. Pages also poll every 15-60 s as a fallback.

## Database tables

`users`, `refresh_tokens`, `businesses`, `business_members`, `services`, `counters`, `queue_sessions`, `queue_tokens`, `appointments`, `notifications`, `audit_logs`.

Phase 2 schema changes:

- `services`: `token_prefix`, `appointments_enabled`, `appointment_duration_minutes`, `appointment_slot_capacity`, `appointment_daily_capacity`, `appointment_hours`, `booking_version`
- `queue_sessions`: `max_capacity`, `token_prefix`, `paused_at`
- `queue_tokens`: `recall_count`, `skipped_at`, `no_show_at`, `approaching_notified_at`; partial unique indexes `uq_queue_tokens_active_customer`, `uq_queue_tokens_counter_in_use`
- `appointments`: `confirmed_at`, `checked_in_at`, `completed_at`, `cancelled_at`, `cancellation_reason`; partial unique index `uq_appointments_active_customer_slot`

Enums are stored as `VARCHAR` with CHECK constraints and datetimes are stored in UTC (timezone-aware on PostgreSQL), so the same models work on SQLite and PostgreSQL. Working hours are validated JSON (`[{day_of_week, is_closed, open_time, close_time}]`).

---

## Known limitations

- **Migrations.** Tables are created with `create_all`, and startup refuses to run against an outdated schema. Add Alembic before keeping real data across schema changes.
- **SQLite under heavy write load.** Joins and bookings are serialized per queue or service. SQLite has a single writer, so very high concurrency can hit its 5 s lock timeout; the API then returns `503` with `Retry-After`. Use PostgreSQL for real multi-user load.
- **WebSockets are in-process.** Running several backend processes would need a shared pub/sub (e.g. Redis) behind `websocket/manager.py`; until then, the polling fallback keeps pages current.
- **One service per counter.** A counter serves one service at a time; it can be moved between services but cannot serve several at once.
- **Email/SMS.** Not configured. Notifications are in-app only, and password reset links are written to the backend log.
- **Appointments and queues** are separate: checking in an appointment does not create a queue token.
- **Hardening.** There is no rate limiting on login or joining yet, and tokens are kept in `localStorage` rather than httpOnly cookies.
