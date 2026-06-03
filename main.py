import os
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from models import (
    ChatRequest, ChatResponse, RepContext,
    LowPerformingResponse, StoreItem,
    StoreProductsResponse, ProductItem,
    RecommendationsResponse, VisitRecommendation, ProductPushRecommendation,
    AlertsResponse, Alert,
    HealthResponse,
)
from database import get_connection, get_rep, is_db_ready
import ai_engine

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="SaneForce AI Sales Assistant",
    description="AI-powered sales intelligence API for SaneForce field sales teams.",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten to specific domains in production
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Security headers middleware ───────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


def _require_rep(rep_id: int):
    rep = get_rep(rep_id)
    if not rep:
        raise HTTPException(status_code=404, detail=f"Rep with id {rep_id} not found")
    return rep


# ── /chat ──────────────────────────────────────────────────────────────────────
# Stricter limit: 10 AI calls/minute per IP (each call hits Groq)

@app.post("/chat", response_model=ChatResponse, tags=["AI"])
@limiter.limit("10/minute")
def chat(request: Request, body: ChatRequest):
    """Ask the AI any question about your stores, products, visits, or sales strategy."""
    result = ai_engine.chat(body.question, body.rep_id)
    if not result["rep"]:
        raise HTTPException(status_code=404, detail="Rep not found")
    rep = result["rep"]
    return ChatResponse(
        answer=result["answer"],
        query_executed=result.get("query_executed"),
        data_freshness="live",
        rep_context=RepContext(
            rep_id=rep["rep_id"],
            name=rep["name"],
            territory=rep["territory"],
        ),
    )


# ── /stores/low-performing ────────────────────────────────────────────────────

@app.get("/stores/low-performing", response_model=LowPerformingResponse, tags=["Stores"])
@limiter.limit("30/minute")
def low_performing_stores(request: Request, rep_id: int = Query(..., ge=1, description="Your rep ID")):
    """Bottom 5 stores by revenue this month for your territory. Pure SQL — no AI."""
    rep = _require_rep(rep_id)
    start_of_month = date.today().replace(day=1).isoformat()
    today = date.today().isoformat()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                s.store_id,
                s.store_name,
                s.location,
                COALESCE(SUM(sl.revenue), 0) AS revenue_this_month,
                s.last_visit_date
            FROM stores s
            LEFT JOIN sales sl
                ON sl.store_id = s.store_id
                AND sl.sale_date BETWEEN ? AND ?
            WHERE s.rep_id = ?
            GROUP BY s.store_id
            ORDER BY revenue_this_month ASC
            LIMIT 5
            """,
            (start_of_month, today, rep["rep_id"]),
        ).fetchall()

    stores = []
    for r in rows:
        lv = r["last_visit_date"]
        days = (date.today() - date.fromisoformat(lv)).days if lv else None
        stores.append(
            StoreItem(
                store_id=r["store_id"],
                store_name=r["store_name"],
                location=r["location"],
                revenue_this_month=r["revenue_this_month"],
                last_visit_date=lv,
                days_since_visit=days,
            )
        )
    return LowPerformingResponse(stores=stores)


# ── /stores/{store_id}/products ───────────────────────────────────────────────

@app.get("/stores/{store_id}/products", response_model=StoreProductsResponse, tags=["Stores"])
@limiter.limit("30/minute")
def store_products(request: Request, store_id: int, rep_id: int = Query(..., ge=1, description="Your rep ID")):
    """Product sell-through breakdown for a specific store this month."""
    _require_rep(rep_id)
    start_of_month = date.today().replace(day=1).isoformat()
    today = date.today().isoformat()

    with get_connection() as conn:
        store = conn.execute(
            "SELECT * FROM stores WHERE store_id = ?", (store_id,)
        ).fetchone()
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

        rows = conn.execute(
            """
            SELECT
                p.product_name,
                p.sku,
                COALESCE(SUM(sl.units_sold), 0) AS units_sold_this_month
            FROM products p
            LEFT JOIN sales sl
                ON sl.product_id = p.product_id
                AND sl.store_id = ?
                AND sl.sale_date BETWEEN ? AND ?
            GROUP BY p.product_id
            ORDER BY units_sold_this_month DESC
            """,
            (store_id, start_of_month, today),
        ).fetchall()

    products = []
    for r in rows:
        units = r["units_sold_this_month"]
        status = "selling_well" if units >= 10 else ("slow_moving" if units > 0 else "not_selling")
        products.append(
            ProductItem(
                product_name=r["product_name"],
                sku=r["sku"],
                units_sold_this_month=units,
                status=status,
            )
        )
    return StoreProductsResponse(
        store_id=store_id,
        store_name=store["store_name"],
        products=products,
    )


# ── /recommendations ──────────────────────────────────────────────────────────

@app.get("/recommendations", response_model=RecommendationsResponse, tags=["AI"])
@limiter.limit("20/minute")
def recommendations(request: Request, rep_id: int = Query(..., ge=1, description="Your rep ID")):
    """AI-generated visit priority list and product push suggestions."""
    rep = _require_rep(rep_id)
    today = date.today()
    week_ago = (today - timedelta(days=7)).isoformat()
    two_weeks_ago = (today - timedelta(days=14)).isoformat()
    start_of_month = today.replace(day=1).isoformat()

    with get_connection() as conn:
        visit_candidates = conn.execute(
            """
            SELECT
                s.store_id,
                s.store_name,
                s.last_visit_date,
                COALESCE(SUM(CASE WHEN sl.sale_date >= ? THEN sl.revenue ELSE 0 END), 0) AS rev_this_week,
                COALESCE(SUM(CASE WHEN sl.sale_date BETWEEN ? AND ? THEN sl.revenue ELSE 0 END), 0) AS rev_prev_week
            FROM stores s
            LEFT JOIN sales sl ON sl.store_id = s.store_id
            WHERE s.rep_id = ?
              AND (s.last_visit_date IS NULL OR s.last_visit_date <= ?)
            GROUP BY s.store_id
            ORDER BY rev_this_week ASC
            LIMIT 5
            """,
            (week_ago, two_weeks_ago, week_ago, rep["rep_id"], week_ago),
        ).fetchall()

        push_candidates = conn.execute(
            """
            SELECT DISTINCT
                s.store_id,
                s.store_name,
                p.product_name
            FROM stores s
            JOIN products p
            LEFT JOIN sales zero_sale
                ON zero_sale.store_id = s.store_id
                AND zero_sale.product_id = p.product_id
                AND zero_sale.sale_date >= ?
            JOIN sales other_sale
                ON other_sale.product_id = p.product_id
                AND other_sale.store_id != s.store_id
                AND other_sale.sale_date >= ?
            WHERE s.rep_id = ?
              AND zero_sale.sale_id IS NULL
            LIMIT 5
            """,
            (start_of_month, start_of_month, rep["rep_id"]),
        ).fetchall()

    visit_recs = []
    for r in visit_candidates:
        lv = r["last_visit_date"]
        days = (today - date.fromisoformat(lv)).days if lv else 99
        drop_pct = 0
        if r["rev_prev_week"] > 0:
            drop_pct = round((r["rev_prev_week"] - r["rev_this_week"]) / r["rev_prev_week"] * 100)
        priority = "high" if (days >= 10 or drop_pct >= 25) else "medium"
        reason_parts = []
        if days >= 7:
            reason_parts.append(f"not visited in {days} days")
        if drop_pct > 0:
            reason_parts.append(f"revenue down {drop_pct}% vs last week")
        visit_recs.append(
            VisitRecommendation(
                store_id=r["store_id"],
                store_name=r["store_name"],
                reason=", ".join(reason_parts) if reason_parts else "low recent activity",
                priority=priority,
            )
        )

    push_recs = [
        ProductPushRecommendation(
            store_id=r["store_id"],
            product_name=r["product_name"],
            reason=f"Top seller at other stores but zero movement at {r['store_name']} this month",
        )
        for r in push_candidates
    ]

    return RecommendationsResponse(
        visit_recommendations=visit_recs,
        product_push_recommendations=push_recs,
    )


# ── /alerts ───────────────────────────────────────────────────────────────────

@app.get("/alerts", response_model=AlertsResponse, tags=["Alerts"])
@limiter.limit("30/minute")
def alerts(request: Request, rep_id: int = Query(..., ge=1, description="Your rep ID")):
    """Proactive alerts: unvisited stores, sales drops, stalled products."""
    rep = _require_rep(rep_id)
    today = date.today()
    week_ago = (today - timedelta(days=7)).isoformat()
    two_weeks_ago = (today - timedelta(days=14)).isoformat()

    with get_connection() as conn:
        unvisited = conn.execute(
            """
            SELECT store_name, location, last_visit_date
            FROM stores
            WHERE rep_id = ?
              AND (last_visit_date IS NULL OR last_visit_date <= ?)
            ORDER BY last_visit_date ASC
            """,
            (rep["rep_id"], week_ago),
        ).fetchall()

        drops = conn.execute(
            """
            SELECT
                s.store_name,
                COALESCE(SUM(CASE WHEN sl.sale_date >= ? THEN sl.revenue ELSE 0 END), 0) AS this_week,
                COALESCE(SUM(CASE WHEN sl.sale_date BETWEEN ? AND ? THEN sl.revenue ELSE 0 END), 0) AS last_week
            FROM stores s
            LEFT JOIN sales sl ON sl.store_id = s.store_id
            WHERE s.rep_id = ?
            GROUP BY s.store_id
            HAVING last_week > 0 AND (last_week - this_week) * 1.0 / last_week >= 0.20
            ORDER BY (last_week - this_week) DESC
            LIMIT 5
            """,
            (week_ago, two_weeks_ago, week_ago, rep["rep_id"]),
        ).fetchall()

    result = []
    for r in unvisited:
        lv = r["last_visit_date"]
        days = (today - date.fromisoformat(lv)).days if lv else "unknown number of"
        severity = "high" if (isinstance(days, int) and days >= 10) else "medium"
        result.append(Alert(
            type="store_not_visited",
            message=f"{r['store_name']} ({r['location']}) has not been visited in {days} days",
            severity=severity,
        ))

    for r in drops:
        drop_pct = round((r["last_week"] - r["this_week"]) / r["last_week"] * 100)
        severity = "high" if drop_pct >= 30 else "medium"
        result.append(Alert(
            type="sales_drop",
            message=f"{r['store_name']} revenue dropped {drop_pct}% vs last week",
            severity=severity,
        ))

    return AlertsResponse(alerts=result)


# ── /health ───────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    return HealthResponse(
        status="ok",
        version="1.0.0",
        db="connected" if is_db_ready() else "error",
    )


# ── startup message ───────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    port = os.environ.get("PORT", "8000")
    print("\n" + "=" * 55)
    print("  SaneForce AI Sales Assistant — POC")
    print("=" * 55)
    print(f"  API Base URL : http://localhost:{port}")
    print(f"  Swagger Docs : http://localhost:{port}/docs")
    print("=" * 55 + "\n")
