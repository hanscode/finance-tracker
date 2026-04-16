# 💰 Finance Tracker

> Your money. Your server. Your privacy.

A self-hosted personal finance application built with the [ONCE philosophy](https://once.com/) in mind — own your software, own your data, no subscriptions.

---

## Why?

Most finance apps are SaaS: your most sensitive data lives on someone else's server, behind a monthly fee. Finance Tracker is different:

- **Self-hosted** — runs on your own server, VPS, or even a Raspberry Pi
- **SQLite-powered** — no external database to configure or maintain
- **Private by design** — your financial data never leaves your infrastructure
- **One command to deploy** — `docker compose up` and you're running

## Features

- **Transaction tracking** — income, expenses, transfers, savings, investments, donations
- **50/30/20 budgeting** — automatic categorization into needs, wants, and savings
- **Recurring transactions** — auto-generated bills and income on schedule
- **Quick templates** — one-click entry for frequent transactions
- **Savings goals** — visual progress tracking toward financial targets
- **Debt tracking** — monitor payoff progress with interest calculations
- **Dashboard** — monthly overview with interactive charts
- **Reports & export** — monthly/annual summaries, CSV and JSON export
- **Dark mode** — light, dark, or follow system preference
- **Multi-currency** — configurable currency with proper formatting
- **Family sharing** — invite members to share one financial account

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.12 |
| Database | SQLite (WAL mode) |
| ORM | SQLAlchemy 2.0 |
| Frontend | React 19 + TypeScript |
| UI | Tailwind CSS v4 + shadcn/ui |
| Charts | Recharts |
| Deploy | Docker + Docker Compose |

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your machine

### Run it

```bash
git clone https://github.com/hanscode/finance-tracker.git
cd finance-tracker
docker compose up
```

Then open:
- **App**: http://localhost:3000
- **API docs**: http://localhost:8000/docs

On first launch, you'll be guided through a setup wizard to create your account.

## Development

### Requirements

- Python 3.12+ (via [pyenv](https://github.com/pyenv/pyenv))
- Node.js 22+
- Docker & Docker Compose

### Local development

```bash
# Clone the repo
git clone https://github.com/hanscode/finance-tracker.git
cd finance-tracker

# Start development environment with hot reload
docker compose up
```

The development setup includes:
- **Backend** hot reload on `http://localhost:8000` (code changes restart automatically)
- **Frontend** hot reload on `http://localhost:3000` (changes appear instantly in the browser)
- **Swagger UI** on `http://localhost:8000/docs` (interactive API documentation)

### Project structure

```
finance-tracker/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── main.py        # App entry point
│   │   ├── config.py      # Settings
│   │   ├── database.py    # SQLAlchemy + SQLite setup
│   │   ├── models/        # Database models
│   │   ├── schemas/       # Pydantic validation
│   │   ├── routers/       # API endpoints
│   │   └── services/      # Business logic
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/          # React application
│   ├── src/
│   │   ├── components/    # UI components (shadcn/ui)
│   │   ├── pages/         # Route pages
│   │   └── lib/           # Utilities
│   ├── Dockerfile
│   └── package.json
├── data/              # SQLite database (volume mounted)
├── docker-compose.yml
├── DESIGN.md          # Full application design document
└── README.md
```

## Design

See [DESIGN.md](DESIGN.md) for the complete application design document, including:
- Data model and entity relationships
- API endpoint reference
- Feature specifications
- Implementation phases

## License

MIT

---

Built with care by [@hanscode](https://github.com/hanscode).
