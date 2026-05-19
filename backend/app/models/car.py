from pydantic import BaseModel
from typing import Optional, List, Any


class ParseQueryRequest(BaseModel):
    query: str


class CarFilters(BaseModel):
    max_price: Optional[int] = None
    min_price: Optional[int] = None
    city: Optional[str] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    max_mileage: Optional[int] = None
    min_year: Optional[int] = None
    make: Optional[str] = None
    model_name: Optional[str] = None
    search_keywords: Optional[str] = None


class CarListing(BaseModel):
    title: str
    price: Optional[int] = None
    price_display: str
    city: Optional[str] = None
    year: Optional[int] = None
    mileage: Optional[int] = None
    mileage_display: Optional[str] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    image: Optional[str] = None
    images: List[str] = []
    url: str
    score: int = 0
    ai_explanation: Optional[str] = None
    condition_note: Optional[str] = None
    source: str = "pakwheels"
    is_recommended: bool = False


class SearchRequest(BaseModel):
    query: str


class SearchResponse(BaseModel):
    query: str
    filters: dict
    cars: List[CarListing]
    total_found: int
    ai_summary: Optional[str] = None
    model_info: dict = {}
    source: str = "live"
