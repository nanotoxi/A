from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import re


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    rep_id: int = Field(..., ge=1)

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        # Strip SQL injection attempts and control characters
        cleaned = re.sub(r"[;\\\x00-\x1f]", "", v).strip()
        if not cleaned:
            raise ValueError("Question must contain readable text")
        return cleaned


class RepContext(BaseModel):
    rep_id: int
    name: str
    territory: str


class ChatResponse(BaseModel):
    answer: str
    query_executed: Optional[str] = None
    data_freshness: str = "live"
    rep_context: RepContext


class StoreItem(BaseModel):
    store_id: int
    store_name: str
    location: str
    revenue_this_month: float
    last_visit_date: Optional[str]
    days_since_visit: Optional[int]


class LowPerformingResponse(BaseModel):
    stores: List[StoreItem]


class ProductItem(BaseModel):
    product_name: str
    sku: str
    units_sold_this_month: int
    status: str


class StoreProductsResponse(BaseModel):
    store_id: int
    store_name: str
    products: List[ProductItem]


class VisitRecommendation(BaseModel):
    store_id: int
    store_name: str
    reason: str
    priority: str


class ProductPushRecommendation(BaseModel):
    store_id: int
    product_name: str
    reason: str


class RecommendationsResponse(BaseModel):
    visit_recommendations: List[VisitRecommendation]
    product_push_recommendations: List[ProductPushRecommendation]


class Alert(BaseModel):
    type: str
    message: str
    severity: str


class AlertsResponse(BaseModel):
    alerts: List[Alert]


class HealthResponse(BaseModel):
    status: str
    version: str
    db: str
