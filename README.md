<div align="center">
  <h1>SkillLedger</h1>
  <p><strong>Verify what you built. Prove what you know.</strong></p>
  <p>An AI-powered developer portfolio platform that transforms your GitHub repositories into verified, evidence-backed proof of your skills — for recruiters who care about real work.</p>

  <p>
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi" />
    <img src="https://img.shields.io/badge/Next.js-15-black?style=flat-square&logo=next.js" />
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python" />
    <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript" />
    <img src="https://img.shields.io/badge/SQLite%20%7C%20PostgreSQL-ready-336791?style=flat-square&logo=postgresql" />
    <img src="https://img.shields.io/badge/GLM--5.1-AI%20Powered-FF4B4B?style=flat-square" />
  </p>
</div>

---

## Screenshots

> Drop your screenshots into `docs/screenshots/` to populate this section.

| Portfolio Page | Dashboard | Repository Analysis |
|---|---|---|
| ![Portfolio](docs/screenshots/portfolio.png) | ![Dashboard](docs/screenshots/dashboard.png) | ![Analysis](docs/screenshots/analysis.png) |

| Skills Panel | Contribution Verification | Deployment Verification |
|---|---|---|
| ![Skills](docs/screenshots/skills.png) | ![Contributions](docs/screenshots/contributions.png) | ![Deployment](docs/screenshots/deployment.png) |

---

## Overview

SkillLedger is a full-stack portfolio intelligence platform. Connect your GitHub account, import repositories, and the system automatically:

1. **Analyzes** your code for complexity, security, and documentation quality
2. **Extracts verified skills** using GLM-5.1 AI with confidence scores and code evidence
3. **Verifies deployments** — live URL scanning, SSL validation, security headers, asset health
4. **Quantifies contributions** — commit history, file ownership, module authorship
5. **Generates a public portfolio** at `/u/{username}` with scores, skill charts, and project cards

No self-reporting. No fluff. Just verifiable proof.

---

## Architecture

```
SkillLedger
├── backend/                  # FastAPI + Python 3.11
│   ├── app/
│   │   ├── api/              # Route handlers (auth, repos, skills, contributions, portfolio)
│   │   ├── services/         # Business logic and AI integrations
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── database/         # Session management, base, migrations
│   │   └── core/             # Config, security utilities
│   ├── alembic/              # Database migrations
│   └── tests/
│
└── frontend/                 # Next.js 15 + TypeScript + Tailwind CSS
    └── src/
        ├── app/
        │   ├── dashboard/    # Authenticated dashboard
        │   ├── repositories/ # Repository detail and analysis views
        │   └── u/[username]/ # Public portfolio page
        ├── components/
        │   ├── auth/
        │   ├── portfolio/    # PortfolioView, score rings, skill bars
        │   └── ui/           # shadcn/ui components
        ├── lib/              # API client, config
        └── types/            # TypeScript interfaces
```

---

## Modules

### GitHub OAuth Authentication
- Secure GitHub OAuth 2.0 login flow
- HTTP-only cookie session management with access and refresh JWTs
- Automatic token refresh middleware

### Repository Import System
- Browse and import GitHub repositories with one click
- Full metadata sync — stars, forks, languages, frameworks, dependencies
- Background cloning and analysis queue

### Repository Intelligence Engine
- Code complexity scoring (0–100)
- Security vulnerability scanning
- Documentation coverage analysis
- Commit history aggregation

### GLM Skill Extraction Service
- Powered by **Zhipu AI GLM-5.1**
- Extracts verified skills with confidence scores (0–100) backed by code evidence
- Categories: Language, Framework, Database, DevOps, AI/ML, Security
- Generates recruiter-friendly project summaries and technical insights

### Deployment Verification Engine
- Auto-discovers live deployment URLs (Vercel, Netlify, Railway, custom domains)
- Validates reachability, SSL certificates, and security response headers
- Asset health scoring and internal link validation
- Deployment Score (0–100)

### Contribution Verification Engine
- Per-contributor commit analysis — additions, deletions, ownership percentage
- Module-level file ownership mapping
- Activity score computation
- Evidence-backed contribution reports

### Dynamic Portfolio Generator
- Public portfolio at `/u/{username}` — fully automated, no manual input required
- **Build Score** = `0.4 × Complexity + 0.3 × Security + 0.3 × Documentation`
- **Proof Score** = `0.5 × Deployment Score + 0.5 × Contribution %`
- Animated SVG score rings and skill confidence bars
- Filterable projects by type, deployment status, and technology stack
- Loading skeleton and SEO-ready metadata per page

---

## API Reference

All endpoints are prefixed with `/api/v1`.

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/auth/github/login` | Get GitHub OAuth redirect URL |
| `GET` | `/auth/github/callback` | OAuth callback handler |
| `GET` | `/auth/me` | Get current authenticated user |
| `POST` | `/auth/logout` | Logout and clear session cookies |
| `POST` | `/auth/refresh` | Rotate access and refresh tokens |

### Repositories

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/repositories/github` | List all GitHub repositories |
| `POST` | `/repositories/import` | Import a repository |
| `GET` | `/repositories` | List imported repositories |
| `GET` | `/repositories/{id}` | Get repository details |
| `GET` | `/repositories/{id}/analysis` | Get full analysis report |

### Skills and Insights

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/skills/extract/{repo_id}` | Run GLM-5.1 skill extraction |
| `GET` | `/skills/{repo_id}` | Get extracted skills |
| `GET` | `/insights/{repo_id}` | Get recruiter-facing project insights |

### Deployments

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/deployments/discover/{repo_id}` | Auto-discover deployment URL |
| `POST` | `/deployments/verify/{repo_id}` | Run full deployment scan |
| `GET` | `/deployments/report/{repo_id}` | Get latest deployment report |

### Contributions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/contributions/analyze/{repo_id}` | Run contribution analysis |
| `GET` | `/contributions/{repo_id}` | Get contribution report |
| `GET` | `/contributions/{repo_id}/contributors` | List all contributors |
| `GET` | `/contributions/{repo_id}/ownership` | Module ownership breakdown |

### Portfolio (Public)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/portfolio/{username}` | Full portfolio aggregation |
| `GET` | `/portfolio/{username}/projects` | Projects list |
| `GET` | `/portfolio/{username}/skills` | Grouped skill categories |

---

## Database Schema

```
users ──────────────────── repositories
                               │
           ┌───────────────────┼──────────────────────┐
           │                   │                      │
  repository_analyses     contributors         deployment_reports
  (complexity, security,  (commits, ownership  (url, ssl, score,
   documentation scores)   %, activity score)   headers, provider)
           │
  ┌────────┼──────────────────────┐
  │        │                      │
skills  project_insights  contribution_reports  module_ownerships
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Tanmay1214/SkillLedger.git
cd SkillLedger
```

### 2. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env — add your GitHub OAuth credentials and GLM API key

# Apply database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (optional — defaults to localhost:8000)
cp .env.example .env.local

# Start the development server
npm run dev
```

### 4. Access the application

| URL | Description |
|-----|-------------|
| `http://localhost:3000` | Main application |
| `http://localhost:8000/docs` | Interactive API documentation |
| `http://localhost:3000/u/{username}` | Public portfolio page |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | SQLite or PostgreSQL connection string |
| `GITHUB_CLIENT_ID` | Yes | From GitHub OAuth App settings |
| `GITHUB_CLIENT_SECRET` | Yes | From GitHub OAuth App settings |
| `JWT_SECRET` | Yes | Random secret — generate with `openssl rand -hex 32` |
| `GLM_API_KEY` | Yes | From [Zhipu AI Open Platform](https://open.bigmodel.cn/) — used for GLM-5.1 |
| `GEMINI_API_KEY` | No | Optional — reserved for future integrations |
| `FRONTEND_URL` | Yes | `http://localhost:3000` in development |
| `CORS_ORIGINS` | Yes | Comma-separated list of allowed origins |

### Setting up GitHub OAuth

1. Go to [GitHub Developer Settings](https://github.com/settings/developers) and create a new OAuth App
2. Set **Homepage URL** to `http://localhost:3000`
3. Set **Authorization callback URL** to `http://localhost:8000/api/v1/auth/github/callback`
4. Copy the **Client ID** and **Client Secret** into your `.env`

### Getting a GLM-5.1 API Key

1. Register at [Zhipu AI Open Platform](https://open.bigmodel.cn/)
2. Navigate to **API Keys** in your dashboard
3. Create a new key and set it as `GLM_API_KEY` in your `.env`

---

## Docker Compose

```bash
# Start all services (backend, frontend, PostgreSQL)
docker-compose up -d

# Apply database migrations
docker-compose exec backend alembic upgrade head
```

---

## Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend type check
cd frontend
npx tsc --noEmit

# Frontend production build
npm run build
```

---

## Roadmap

- [ ] Shareable portfolio cards with Open Graph image generation
- [ ] PDF export of verified portfolio
- [ ] Recruiter view — side-by-side candidate comparison
- [ ] Webhook-based auto-refresh on repository push events
- [ ] GitHub identity verification via email

---

## Contributing

Pull requests are welcome. For significant changes, please open an issue first to discuss the proposed changes.

```bash
git checkout -b feat/your-feature
# implement changes
git push origin feat/your-feature
# open a pull request on GitHub
```

---

## License

MIT © [Tanmay](https://github.com/Tanmay1214)

---

<div align="center">
  <p>Built with FastAPI, Next.js, and Zhipu AI GLM-5.1</p>
  <p>
    <a href="https://github.com/Tanmay1214/SkillLedger">Star this repo</a>
    &nbsp;·&nbsp;
    <a href="https://github.com/Tanmay1214/SkillLedger/issues">Report a Bug</a>
    &nbsp;·&nbsp;
    <a href="https://github.com/Tanmay1214/SkillLedger/issues">Request a Feature</a>
  </p>
</div>
