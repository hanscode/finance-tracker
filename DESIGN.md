# Finance Tracker — Application Design Document

> Your money. Your server. Your privacy.

A self-hosted personal finance application following the ONCE philosophy by 37signals:
own your software, own your data, no subscriptions.

---

## 1. Vision & Philosophy

- **Self-hosted**: anyone can run it on their own server (Docker, VPS, Raspberry Pi)
- **Privacy-first**: financial data never leaves the user's server
- **SQLite-powered**: zero external database dependencies
- **Simple to deploy**: `docker compose up` and you're running
- **50/30/20 budget model**: opinionated but configurable

---

## 2. User Model

**One installation = one account = one shared financial life.**

Following the ONCE philosophy: each installation is a single-tenant instance.
There is no public registration — the owner sets up the account during installation,
and can optionally invite family members to share the same financial data.

### Roles

| Role | Can add transactions | Can manage categories | Can change settings | Can invite members | Can delete account |
|------|---------------------|----------------------|--------------------|--------------------|-------------------|
| **Owner** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Admin** | ✓ | ✓ | ✓ | ✓ | ✗ |
| **Member** | ✓ | ✗ | ✗ | ✗ | ✗ |

- **Owner**: the person who installed the app. One per installation. Full control.
- **Admin**: trusted family member with nearly full access (e.g., spouse).
- **Member**: can view and add transactions but cannot modify settings or categories.

All users share the same financial data — this is not a multi-tenant SaaS.
If someone else wants their own finance tracker, they install their own instance.

### Authentication

Two methods available, depending on server configuration:

**Magic Link (primary, when SMTP is configured):**
- User enters email → receives a link with a one-time token
- Token expires after 15 minutes
- No passwords to remember or manage
- Requires SMTP settings (email server)

**Email + Password (fallback, always available):**
- Traditional login with email and hashed password (bcrypt)
- Used when SMTP is not configured
- Owner chooses the auth method during setup

**Session management:**
- JWT tokens for API authentication
- Configurable session expiration
- Ability to revoke sessions (log out from all devices)

---

## 3. Core Features

### 3.1 Transactions

The fundamental unit of the app. Every financial movement is a transaction.

| Field | Description |
|-------|-------------|
| **Type** | `income`, `expense`, `transfer`, `savings`, `investment`, `donation` |
| **Amount** | Decimal value in user's configured currency |
| **Category** | User-defined category (e.g., "Groceries", "Salary") |
| **Date** | When the transaction occurred |
| **Description** | Optional note about the transaction |
| **Budget bucket** | 50/30/20 classification: `need`, `want`, or `savings` |
| **Tags** | Optional tags for flexible grouping (e.g., "vacation", "tax-deductible") |
| **Is recurring** | Whether this transaction was auto-generated from a recurring rule |

### 3.2 Categories

User-customizable categories with sensible defaults.

**Default categories (seeded on account creation):**

| Category | Type | Budget Bucket |
|----------|------|---------------|
| Salary | income | — |
| Freelance | income | — |
| Rent/Mortgage | expense | need |
| Utilities | expense | need |
| Groceries | expense | need |
| Transportation | expense | need |
| Insurance | expense | need |
| Healthcare | expense | need |
| Dining Out | expense | want |
| Entertainment | expense | want |
| Shopping | expense | want |
| Subscriptions | expense | want |
| Travel | expense | want |
| Emergency Fund | savings | savings |
| Investments | investment | savings |
| Debt Payment | expense | need |
| Donations | donation | want |
| Education | expense | need |
| Personal Care | expense | want |
| Other | expense | — |

Users can:
- Create custom categories
- Assign a budget bucket (need/want/savings) to each
- Set an icon/color per category
- Archive (soft-delete) categories

### 3.3 Recurring Transactions

Two mechanisms:

#### A. Automatic Recurrence Rules
Define a rule and the app auto-generates transactions on schedule.

| Field | Description |
|-------|-------------|
| **Base transaction** | Template: amount, category, type, description |
| **Frequency** | `weekly`, `biweekly`, `monthly`, `quarterly`, `yearly` |
| **Start date** | When recurrence begins |
| **End date** | Optional — when recurrence stops |
| **Next occurrence** | Calculated: when the next transaction will be created |
| **Active** | Can be paused/resumed |

Examples: salary (biweekly), rent (monthly), Netflix (monthly), car insurance (quarterly).

#### B. Quick Templates
Saved transaction templates for one-click entry of frequent but non-periodic expenses.

Examples: "Coffee at Starbucks — $5.50 — Dining Out", "Gas — $45 — Transportation".

### 3.4 Budget (50/30/20)

The budgeting engine automatically tracks spending against the 50/30/20 rule based on the user's net income.

| Bucket | Target % | What it covers |
|--------|----------|----------------|
| **Needs** | 50% | Rent, utilities, groceries, insurance, minimum debt payments |
| **Wants** | 30% | Dining, entertainment, subscriptions, shopping, travel |
| **Savings** | 20% | Emergency fund, investments, extra debt payments, donations |

**How it works:**
1. User sets their monthly net income (or the app calculates from income transactions)
2. Each expense is automatically categorized into a bucket via its category
3. Dashboard shows real-time progress: "Needs: $1,200 / $2,000 (60%)"
4. Alerts when approaching or exceeding a bucket limit

**Budget percentages are configurable** — user can adjust to 60/20/20 or any split that totals 100%.

### 3.5 Savings Goals

Track progress toward specific financial goals.

| Field | Description |
|-------|-------------|
| **Name** | e.g., "Emergency Fund", "Vacation to Japan" |
| **Target amount** | How much to save |
| **Current amount** | Calculated from linked savings transactions |
| **Target date** | Optional deadline |
| **Monthly target** | Calculated: how much to save per month to reach goal on time |
| **Category** | Linked category for auto-tracking |
| **Color/Icon** | Visual identity |

Dashboard shows progress bars and projections: "On track" / "Behind by $200".

### 3.6 Debt Tracking

Track debt repayment progress.

| Field | Description |
|-------|-------------|
| **Name** | e.g., "Student Loan", "Credit Card" |
| **Original amount** | Total debt when started tracking |
| **Current balance** | Calculated from payment transactions |
| **Interest rate** | APR for projection calculations |
| **Minimum payment** | Monthly minimum required |
| **Category** | Linked category for auto-tracking |

### 3.7 Dashboard & Reports

#### Monthly Dashboard
- **Income vs Expenses**: bar chart comparison
- **50/30/20 progress**: visual gauges for each bucket
- **Spending by category**: donut/pie chart
- **Recent transactions**: last 10-15 transactions
- **Savings goals progress**: horizontal progress bars
- **Debt payoff progress**: remaining balances
- **Net worth trend**: simple line chart (assets - debts over time)

#### Reports
- **Monthly summary**: total income, expenses, savings rate
- **Category breakdown**: detailed spending per category with month-over-month comparison
- **Trend analysis**: spending trends over 3, 6, 12 months
- **Annual overview**: yearly totals and averages
- **Budget adherence**: how well user stuck to 50/30/20 over time

#### Export
- **CSV export**: transactions, summaries, or custom date ranges
- **JSON export**: full data backup (for portability)
- **PDF report**: formatted monthly/annual summary (future enhancement)

---

## 4. Settings

### 4.1 Appearance
- **Theme**: light / dark / system (follows OS preference)
- **Accent color**: primary UI color (default: app brand color)

### 4.2 Regional
- **Currency**: configurable (USD, EUR, GBP, MXN, CAD, etc.)
  - Symbol, decimal separator, thousands separator
  - One active currency at a time
- **Date format**: `MM/DD/YYYY`, `DD/MM/YYYY`, `YYYY-MM-DD`
- **First day of week**: Sunday or Monday
- **Language**: English (v1), extensible for i18n later

### 4.3 Budget
- **Monthly net income**: base for 50/30/20 calculations
- **Budget split**: default 50/30/20, adjustable
- **Budget period**: monthly (default), could support weekly/biweekly

### 4.4 Notifications (future)
- **Budget alerts**: when approaching bucket limits (80%, 100%)
- **Bill reminders**: upcoming recurring transactions
- **Savings milestones**: when reaching goal checkpoints

### 4.5 Data
- **Export all data**: full JSON backup
- **Import transactions**: CSV import
- **Delete account**: remove all user data permanently

---

## 5. Data Model (Entity Relationship)

```
┌───────────────────────────────────────┐
│           Account (singleton)         │
├───────────────────────────────────────┤
│ id                                    │
│ name (e.g., "The Smith Family")       │
│ setup_completed                       │
│ auth_method (magic_link / password)   │
│ smtp_host (nullable)                  │
│ smtp_port (nullable)                  │
│ smtp_user (nullable)                  │
│ smtp_password (nullable, encrypted)   │
│ created_at                            │
└──────────────────┬────────────────────┘
                   │ one-to-many
                   ▼
┌───────────────────────────────────────┐
│              User                     │
├───────────────────────────────────────┤
│ id                                    │
│ account_id (FK)                       │
│ email                                 │
│ name                                  │
│ password_hash (nullable, for pwd auth)│
│ role (owner / admin / member)         │
│ is_active                             │
│ created_at                            │
└──────────────────┬────────────────────┘
                   │
        ┌──────────┼──────────────────────────────┐
        ▼          ▼                              ▼
┌──────────────┐ ┌──────────────┐         ┌──────────────┐
│   Session    │ │   Category   │         │     Tag      │
├──────────────┤ ├──────────────┤         ├──────────────┤
│ id           │ │ id           │         │ id           │
│ user_id (FK) │ │ account_id   │         │ account_id   │
│ token        │ │ name         │         │ name         │
│ expires_at   │ │ type         │         └──────────────┘
│ created_at   │ │ icon         │                │
└──────────────┘ │ color        │                │ (many-to-many)
                 │ budget_bucket│                │
                 │ is_default   │         ┌──────┴───────┐
                 │ archived     │         │transaction_tag│
                 └──────┬───────┘         └──────┬───────┘
                        │                        │
                        ▼                        │
        ┌───────────────────────────────────────┐│
        │         Transaction                   ├┘
        ├───────────────────────────────────────┤
        │ id                                    │
        │ account_id (FK)                       │
        │ created_by (FK → User)                │
        │ category_id (FK)                      │
        │ type (income/expense/transfer/etc.)   │
        │ amount                                │
        │ description                           │
        │ date                                  │
        │ budget_bucket (need/want/savings)     │
        │ is_recurring                          │
        │ recurring_rule_id (FK, nullable)      │
        │ created_at                            │
        │ updated_at                            │
        └───────────────────────────────────────┘

        ┌───────────────────────────────────────┐
        │       Recurring Rule                  │
        ├───────────────────────────────────────┤
        │ id                                    │
        │ account_id (FK)                       │
        │ category_id (FK)                      │
        │ type                                  │
        │ amount                                │
        │ description                           │
        │ frequency                             │
        │ start_date                            │
        │ end_date (nullable)                   │
        │ next_occurrence                       │
        │ is_active                             │
        └───────────────────────────────────────┘

        ┌───────────────────────────────────────┐
        │       Quick Template                  │
        ├───────────────────────────────────────┤
        │ id                                    │
        │ account_id (FK)                       │
        │ category_id (FK)                      │
        │ type                                  │
        │ amount                                │
        │ description                           │
        │ budget_bucket                         │
        └───────────────────────────────────────┘

        ┌───────────────────────────────────────┐
        │       Savings Goal                    │
        ├───────────────────────────────────────┤
        │ id                                    │
        │ account_id (FK)                       │
        │ name                                  │
        │ target_amount                         │
        │ target_date (nullable)                │
        │ category_id (FK, nullable)            │
        │ icon                                  │
        │ color                                 │
        │ is_completed                          │
        └───────────────────────────────────────┘

        ┌───────────────────────────────────────┐
        │          Debt                         │
        ├───────────────────────────────────────┤
        │ id                                    │
        │ account_id (FK)                       │
        │ name                                  │
        │ original_amount                       │
        │ interest_rate                         │
        │ minimum_payment                       │
        │ category_id (FK, nullable)            │
        └───────────────────────────────────────┘

        ┌───────────────────────────────────────┐
        │      Account Settings                 │
        ├───────────────────────────────────────┤
        │ id                                    │
        │ account_id (FK, unique)               │
        │ theme (light/dark/system)             │
        │ currency (USD, EUR, MXN...)           │
        │ date_format                           │
        │ first_day_of_week                     │
        │ monthly_income                        │
        │ budget_needs_pct (default: 50)        │
        │ budget_wants_pct (default: 30)        │
        │ budget_savings_pct (default: 20)      │
        └───────────────────────────────────────┘
```

**Key design decisions:**
- **Account is a singleton** — enforced by a unique constraint (same pattern as 37signals' Campfire/Writebook)
- **Data belongs to the Account, not individual users** — all members see the same transactions, categories, goals, etc.
- **`created_by` on Transaction** — tracks who added each transaction, for accountability
- **Settings are account-level** — theme, currency, and budget config are shared (everyone sees the same dashboard)
- **Categories and Tags are account-scoped** — shared across all members

---

## 6. API Endpoints (REST)

### Setup (first-time only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/setup/status` | Check if setup is completed |
| POST | `/api/setup` | Initial setup: create account + owner user |

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login with email + password |
| POST | `/api/auth/magic-link` | Request magic link via email |
| POST | `/api/auth/magic-link/verify` | Verify magic link token |
| GET | `/api/auth/me` | Get current user info |
| POST | `/api/auth/logout` | Revoke current session |

### Members (owner/admin only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/members` | List account members |
| POST | `/api/members/invite` | Invite a new member via email |
| PUT | `/api/members/{id}/role` | Change member role |
| DELETE | `/api/members/{id}` | Remove member from account |

### Transactions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/transactions` | List (paginated, filterable by date/category/type) |
| POST | `/api/transactions` | Create transaction |
| GET | `/api/transactions/{id}` | Get single transaction |
| PUT | `/api/transactions/{id}` | Update transaction |
| DELETE | `/api/transactions/{id}` | Delete transaction |

### Categories
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/categories` | List user's categories |
| POST | `/api/categories` | Create category |
| PUT | `/api/categories/{id}` | Update category |
| DELETE | `/api/categories/{id}` | Archive category |

### Recurring Rules
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/recurring` | List recurring rules |
| POST | `/api/recurring` | Create recurring rule |
| PUT | `/api/recurring/{id}` | Update rule |
| DELETE | `/api/recurring/{id}` | Delete rule |
| POST | `/api/recurring/{id}/pause` | Pause/resume rule |

### Quick Templates
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/templates` | List templates |
| POST | `/api/templates` | Create template |
| POST | `/api/templates/{id}/apply` | Create transaction from template |
| PUT | `/api/templates/{id}` | Update template |
| DELETE | `/api/templates/{id}` | Delete template |

### Budget
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/budget/current` | Current month's 50/30/20 status |
| GET | `/api/budget/{year}/{month}` | Specific month's budget |

### Savings Goals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/goals` | List savings goals |
| POST | `/api/goals` | Create goal |
| PUT | `/api/goals/{id}` | Update goal |
| DELETE | `/api/goals/{id}` | Delete goal |

### Debts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/debts` | List debts |
| POST | `/api/debts` | Create debt |
| PUT | `/api/debts/{id}` | Update debt |
| DELETE | `/api/debts/{id}` | Delete debt |

### Dashboard & Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Monthly dashboard data |
| GET | `/api/reports/monthly/{year}/{month}` | Monthly report |
| GET | `/api/reports/annual/{year}` | Annual report |
| GET | `/api/reports/trends` | Spending trends |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get user settings |
| PUT | `/api/settings` | Update settings |

### Export / Import
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/export/csv` | Export transactions as CSV |
| GET | `/api/export/json` | Export all data as JSON |
| POST | `/api/import/csv` | Import transactions from CSV |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | API health check |

---

## 7. Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Setup | `/setup` | First-time setup wizard (create account + owner) |
| Login | `/login` | Email + password or magic link |
| Dashboard | `/` | Monthly overview with charts |
| Transactions | `/transactions` | List, filter, search, add transactions |
| Categories | `/categories` | Manage categories |
| Budget | `/budget` | 50/30/20 view with progress |
| Recurring | `/recurring` | Manage recurring rules + templates |
| Goals | `/goals` | Savings goals with progress bars |
| Debts | `/debts` | Debt tracking |
| Reports | `/reports` | Monthly/annual reports |
| Settings | `/settings` | Theme, currency, budget config |
| Members | `/settings/members` | Invite/manage members (owner/admin only) |

---

## 8. Implementation Phases (Updated)

| Phase | Focus | Key Deliverables |
|-------|-------|-----------------|
| 1 ✅ | Project setup | Docker, FastAPI, React, Tailwind, shadcn/ui |
| 2 ✅ | Data models + migrations | SQLAlchemy models (13 tables), Alembic setup |
| 3 ✅ | Auth system | Setup wizard, password login, JWT, HTTPBearer, revocable sessions |
| 4 | Categories + Transactions API | CRUD endpoints with validation |
| 5 | Frontend foundation | React Router, layouts, auth pages |
| 6 | Transactions UI | Transaction list, forms, filters |
| 7 | Budget engine (50/30/20) | Budget calculations, budget page |
| 8 | Recurring transactions | Rules, templates, auto-generation |
| 9 | Savings goals + Debt tracking | Goals UI, debt tracking UI |
| 10 | Dashboard + Charts | Dashboard with Recharts visualizations |
| 11 | Reports + Export | Monthly/annual reports, CSV/JSON export |
| 12 | Settings + Theme | Dark mode, currency, date format |
| 13 | Docker production + deploy | Multi-stage build, SSL, one-command deploy |

---

## 9. Tech Stack (Final)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | FastAPI + Python 3.12 | REST API |
| ORM | SQLAlchemy 2.0 | Database abstraction |
| Database | SQLite (WAL mode) | Data storage |
| Migrations | Alembic | Schema versioning |
| Auth | JWT (python-jose) + bcrypt | Authentication |
| Validation | Pydantic v2 | Request/response validation |
| Frontend | React 19 + TypeScript | User interface |
| Build | Vite | Fast dev server + bundling |
| UI | Tailwind CSS v4 + shadcn/ui | Styling + components |
| Charts | Recharts | Data visualization |
| Routing | React Router | Client-side navigation |
| Deploy | Docker + Docker Compose | Containerization |
| Testing | pytest + React Testing Library | Backend + frontend tests |
