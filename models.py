from pydantic import BaseModel
from typing import Optional, List, Any


class ChatRequest(BaseModel):
    question: str
    rep_id: int


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
