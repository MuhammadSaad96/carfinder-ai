from fastapi import APIRouter, HTTPException
from app.models.car import ParseQueryRequest
from app.services.ai.groq_client import parse_query
from app.config import GROQ_API_KEY

router = APIRouter()


@router.post("/parse-query")
async def parse_query_route(request: ParseQueryRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
    filters = await parse_query(request.query)
    return {"query": request.query, "filters": filters}
