# CarFinder AI 🚗

AI-powered car discovery for the Pakistani market. Search in English or Urdu — the AI understands both.

**Example queries:**
- `"Mujhe Islamabad main 20 lakh tak automatic gari chahiye"`
- `"Family car under 25 lakh"`
- `"Honda low mileage automatic"`
- `"Fuel average achi ho under 30 lakh"`

---

## How It Works

1. You type a natural language query (English or Urdu/Roman Urdu)
2. Groq AI extracts structured filters (budget, city, transmission, etc.)
3. Backend scrapes PakWheels with those filters
4. A scoring engine ranks cars by how well they match
5. Groq AI explains why the top cars are good matches
6. Results displayed in a clean, modern UI

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python · FastAPI |
| AI | Groq API (llama-3.3-70b-versatile) |
| Scraping | Playwright · BeautifulSoup4 |
| Frontend | Next.js 14 · TailwindCSS · TypeScript |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- A free [Groq API key](https://console.groq.com)

---

## Setup & Run

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Configure environment
copy .env.example .env
# Edit .env and add your GROQ_API_KEY

# Run
uvicorn app.main:app --reload
```

Backend will be available at `http://localhost:8000`

Verify with: `http://localhost:8000/health`

---

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
copy .env.local.example .env.local
# Edit .env.local if your backend runs on a different port

# Run
npm run dev
```

Frontend will be available at `http://localhost:3000`

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Your Groq API key from console.groq.com |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/parse-query` | Extract filters from natural language |
| `POST` | `/search` | Full search with scraping + AI ranking |

### POST /search
```json
// Request
{ "query": "Honda automatic under 25 lakh Islamabad" }

// Response
{
  "query": "...",
  "filters": { "max_price": 2500000, "transmission": "automatic", "city": "Islamabad" },
  "cars": [ { "title": "...", "price": ..., "ai_explanation": "..." } ],
  "total_found": 12,
  "ai_summary": "Great news! I found...",
  "source": "live"
}
```

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS
│   │   ├── config.py            # Env vars
│   │   ├── models/car.py        # Pydantic models
│   │   ├── routes/
│   │   │   ├── search.py        # POST /search
│   │   │   └── parse_query.py   # POST /parse-query
│   │   └── services/
│   │       ├── ai/groq_client.py      # Groq integration
│   │       ├── scraper/pakwheels.py   # PakWheels scraper
│   │       ├── scraper/fallback_data.py  # Demo data
│   │       └── ranking/engine.py      # Scoring logic
│   └── requirements.txt
│
└── frontend/
    ├── app/
    │   ├── page.tsx             # Home page (search)
    │   └── results/page.tsx     # Results page
    ├── components/
    │   ├── CarCard.tsx          # Individual car card
    │   ├── AISummary.tsx        # AI summary banner
    │   ├── FilterBadges.tsx     # Extracted filter chips
    │   └── LoadingSkeleton.tsx  # Loading state
    └── lib/api.ts               # API client
```

---

## Deployment

### Frontend → Vercel

```bash
cd frontend
npm run build  # verify it builds

# Push to GitHub, then import on vercel.com
# Set env var: NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

### Backend → Railway

1. Go to [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Set root directory to `backend/`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add env var: `GROQ_API_KEY=your_key`
6. After deploy, run: `playwright install chromium` (via Railway shell)

### Backend → Render

1. New Web Service on [render.com](https://render.com)
2. Root directory: `backend`
3. Build: `pip install -r requirements.txt && playwright install chromium`
4. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add env var: `GROQ_API_KEY=your_key`

---

## Fallback Demo Mode

If live PakWheels scraping fails (network issues, rate limiting), the app automatically uses realistic demo data so the UI still works. A "Demo data" badge appears on the results page.

---

## Scoring Logic

Cars are ranked by a scoring algorithm before AI explanation:

| Criteria | Points |
|----------|--------|
| Within budget | +30 |
| Correct transmission | +20 |
| City match | +20 |
| Low mileage (<30k km) | +15 |
| Newer model (≤2 years) | +15 |
| Make/model match | +10 |
| Fuel type match | +8 |

Cars that are way over budget or wrong transmission get negative scores.
