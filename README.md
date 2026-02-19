# MarketView

Institutional-grade market analysis system that aggregates live data from Yahoo Finance, CoinGecko, and FRED into a unified trading terminal with AI-powered report generation.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688)
![React 18](https://img.shields.io/badge/React-18-61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6)

## Features

- **Multi-Asset Dashboard** — Real-time overview of S&P 500, VIX, 10Y Treasury, Bitcoin, Gold, and DXY with yield curve and sector performance charts
- **Market Data Explorer** — Tabbed interface covering Equities (US + global indices), Fixed Income (FRED rates, yield curve, credit spreads), FX (9 pairs + DXY), Commodities (precious metals, energy, agriculture), and Crypto (6 major coins + market overview + fear/greed index)
- **Live/Mock Toggle** — Global sidebar switch to flip between live API data and deterministic mock data; auto-falls back to mock on network failure
- **AI Report Generation** — Multi-level market reports (Executive, Standard, Deep Dive) with optional LLM enhancement via OpenAI, Anthropic, or Google Gemini
- **RAG Data Sources** — Upload PDFs or paste text, embed via local/OpenAI/Gemini models, and search with ChromaDB vector store
- **Macro Analysis** — FRED economic indicators (inflation, growth, labor, rates) with regime detection

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  React Frontend (Vite + Tailwind)         localhost:5173 │
│  Dashboard │ Market Data │ Reports │ Sources │ Health    │
└──────────────────────┬──────────────────────────────────┘
                       │ /api/v1/*
┌──────────────────────▼──────────────────────────────────┐
│  FastAPI Backend                          localhost:8000 │
│                                                         │
│  Routers: health │ data (FRED) │ market │ reports │ src │
│                                                         │
│  Data Layer:                                            │
│    EquityClient (yfinance) ──┐                          │
│    FXClient     (yfinance) ──┤                          │
│    CommodityClient (yfinance)┼── DataAggregator         │
│    CryptoClient (CoinGecko) ─┤                          │
│    FREDClient   (fredapi)  ──┤                          │
│    RedditClient (praw)     ──┘                          │
│                                                         │
│  Analysis: RegimeDetector │ TechnicalAnalyzer │ Corr    │
│  Reports:  ReportBuilder → Markdown / PDF / JSON / HTML │
│  Storage:  SQLite + ChromaDB + Redis (optional)         │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Poetry](https://python-poetry.org/) (Python dependency manager)

### Backend

```bash
# Install dependencies
poetry install

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys (FRED_API_KEY required for macro data)

# Start the API server
uvicorn src.api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000` with Swagger docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI will be available at `http://localhost:5173`. The Vite dev server proxies `/api` and `/health` requests to the backend.

### Mock Mode

No API keys needed to explore the UI — click **Mock** in the sidebar to use built-in sample data for all market endpoints. The backend serves deterministic mock data that matches the exact shape of live responses.

## API Endpoints

### Market Data (`/api/v1/data/market`)

All endpoints accept `?source=live|mock` (default: `live`). On live failure, auto-falls back to mock with `"source": "mock (fallback)"` in the response.

| Endpoint | Description |
|----------|-------------|
| `GET /snapshot` | Quick snapshot — SPX, VIX, DXY, BTC, Gold, Yield Curve |
| `GET /equities` | US indices, global indices, sector performance, VIX |
| `GET /fx` | 9 FX pairs, DXY, USD strength index |
| `GET /commodities` | Precious metals, energy, agriculture, industrial |
| `GET /crypto` | 6 major coins, market overview, fear/greed proxy |

### FRED Data (`/api/v1/data/fred`)

| Endpoint | Description |
|----------|-------------|
| `GET /series` | List available FRED series |
| `GET /series/{name}` | Fetch specific series with optional date range |
| `GET /rates` | Interest rates (Fed Funds, 2Y, 10Y, 30Y) |
| `GET /inflation` | CPI, Core CPI, PCE, breakevens |
| `GET /yield-curve` | Current yield curve snapshot |
| `GET /labor` | Unemployment, payrolls, claims |
| `GET /growth` | GDP, real GDP |
| `GET /credit` | HY and IG credit spreads |

### Reports (`/api/v1/reports`)

| Endpoint | Description |
|----------|-------------|
| `POST /generate` | Generate full report (Level 1-3, optional LLM) |
| `GET /generate/quick` | Quick report generation |
| `GET /llm-providers` | List available LLM providers |
| `GET /` | List saved reports |
| `GET /{id}` | Get report by ID |
| `GET /{id}/download` | Download report (markdown/pdf/json/html) |

### Data Sources (`/api/v1/sources`)

| Endpoint | Description |
|----------|-------------|
| `POST /upload` | Upload PDF for RAG embedding |
| `POST /ingest-text` | Ingest raw text |
| `POST /search` | Semantic search across documents |
| `GET /documents` | List uploaded documents |
| `GET /providers` | List embedding providers |

## Project Structure

```
MarketView/
├── src/
│   ├── api/
│   │   ├── main.py                 # FastAPI app, lifespan, CORS
│   │   └── routers/                # health, data, market, reports, sources
│   ├── ingestion/
│   │   ├── aggregator.py           # DataAggregator — unified data fetching
│   │   ├── market_data/            # EquityClient, FXClient, CommodityClient, CryptoClient
│   │   ├── tier1_core/             # FREDClient
│   │   ├── tier2_sentiment/        # RedditClient
│   │   └── tier3_research/         # PDF processor, vector store, embeddings
│   ├── analysis/                   # Regime detector, technical analyzer, correlations
│   ├── reports/                    # Report builder, formatters, section generators
│   ├── llm/                        # Multi-provider LLM client + prompts
│   ├── storage/                    # SQLAlchemy models + repositories
│   ├── config/                     # Settings + constants
│   └── data/                       # Mock data module
├── frontend/
│   └── src/
│       ├── api/client.ts           # Typed API client (axios)
│       ├── context/                # DataSourceContext (Live/Mock toggle)
│       ├── components/             # Layout, MetricCard, ChartCard, StatusBadge
│       └── pages/                  # Dashboard, MarketData, Reports, DataSources, Health
├── pyproject.toml
└── .env.example
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FRED_API_KEY` | For macro data | [Get a free key](https://fred.stlouisfed.org/docs/api/api_key.html) |
| `REDDIT_CLIENT_ID` | For sentiment | [Create an app](https://www.reddit.com/prefs/apps) |
| `REDDIT_CLIENT_SECRET` | For sentiment | Reddit app secret |
| `DATABASE_URL` | No | Defaults to SQLite (`marketview.db`) |
| `REDIS_URL` | No | Optional caching layer |
| `DEBUG` | No | Defaults to `true` (enables `/docs`) |

## Tech Stack

**Backend:** Python 3.11, FastAPI, SQLAlchemy (async), yfinance, pycoingecko, fredapi, ChromaDB, Redis

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts, Axios

**AI/LLM:** OpenAI, Anthropic, Google Gemini (optional enhancement for reports)

## License

MIT
