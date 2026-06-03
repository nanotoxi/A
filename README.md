# SaneForce AI Sales Assistant — POC

AI-powered sales intelligence API for SaneForce field sales reps.  
Built with FastAPI + Groq (LLaMA 3.3 70B) + SQLite.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your GROQ_API_KEY to .env

python seed_data.py       # populate the SQLite DB
uvicorn main:app --reload
```

## Two Links to Share with Client

```
API Base URL  :  http://localhost:8000
Swagger Docs  :  http://localhost:8000/docs
```

## curl Examples

```bash
# Ask the AI a question
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Which stores should I visit tomorrow?", "rep_id": 1}'

# Get low performing stores
curl "http://localhost:8000/stores/low-performing?rep_id=2"

# Get product breakdown for store 7
curl "http://localhost:8000/stores/7/products?rep_id=2"

# Get AI recommendations
curl "http://localhost:8000/recommendations?rep_id=2"

# Get alerts
curl "http://localhost:8000/alerts?rep_id=2"

# Health check
curl http://localhost:8000/health
```

## Sample Questions for /chat

```
"Which of my stores are underperforming this week?"
"What products are not selling at Store 7?"
"Which stores haven't I visited in over 7 days?"
"What approach has worked best for selling SKU-204?"
"Which sales approach has the highest success rate in my territory?"
"Give me a pre-visit briefing for Store 12"
"Which store had the biggest sales drop this month?"
"What should I push at Store 5 this week?"
"How can I improve my approach for low-tier stores?"
"Compare my performance vs last month"
```

## Rep IDs for Testing

| rep_id | Name          | Role      | Territory     |
|--------|---------------|-----------|---------------|
| 1      | Arjun Mehta   | manager   | Mumbai        |
| 2      | Ravi Sharma   | sales_rep | Mumbai North  |
| 3      | Priya Nair    | sales_rep | Mumbai South  |
| 4      | Suresh Patil  | sales_rep | Pune          |
| 5      | Kavita Joshi  | sales_rep | Ahmedabad     |

## Deploy to Railway

1. Push this folder to a GitHub repo
2. Create a new Railway project → Deploy from GitHub
3. Add environment variable: `GROQ_API_KEY=your_key`
4. Railway auto-detects `railway.toml` — seeds DB and starts the server
