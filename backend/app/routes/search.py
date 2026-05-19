import logging
import asyncio
import concurrent.futures
from typing import Optional
from fastapi import APIRouter, HTTPException
from app.models.car import SearchRequest, SearchResponse, CarListing
from app.services.ai.groq_client import parse_query, generate_explanations, generate_summary, analyze_car_image, generate_model_info
from app.services.scraper.pakwheels import PakWheelsScraper
from app.services.scraper.fallback_data import get_fallback_cars
from app.services.ranking.engine import rank_cars
from app.config import GROQ_API_KEY, TOP_CARS_FOR_AI, TOP_CARS_FOR_VISION
from app import cache as _cache

logger = logging.getLogger(__name__)
router = APIRouter()

_playwright_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="playwright")


def _olx_in_thread(filters: dict) -> list:
    """Run OLX Playwright scraper in its own thread with an isolated event loop."""
    import asyncio as _asyncio
    from app.services.scraper.olx import OLXScraper

    loop = _asyncio.new_event_loop()
    _asyncio.set_event_loop(loop)
    try:
        scraper = OLXScraper()
        return loop.run_until_complete(scraper.scrape(filters, max_results=20))
    except Exception as e:
        logger.error(f"OLX thread error: {e}")
        return []
    finally:
        loop.close()


async def _scrape_pakwheels(filters: dict) -> list:
    try:
        scraper = PakWheelsScraper()
        cars = await asyncio.wait_for(scraper.scrape(filters, max_results=25), timeout=60)
        for c in cars:
            c["source"] = "pakwheels"
        logger.info(f"PakWheels returned {len(cars)} cars")
        return cars
    except asyncio.TimeoutError:
        logger.warning("PakWheels scraper timed out")
        return []
    except Exception as e:
        logger.error(f"PakWheels scraper error: {e}")
        return []


async def _scrape_olx(filters: dict) -> list:
    try:
        loop = asyncio.get_running_loop()
        cars = await asyncio.wait_for(
            loop.run_in_executor(_playwright_pool, _olx_in_thread, filters),
            timeout=65,
        )
        result = cars or []
        logger.info(f"OLX returned {len(result)} cars")
        return result
    except asyncio.TimeoutError:
        logger.warning("OLX scraper timed out (65s)")
        return []
    except Exception as e:
        logger.error(f"OLX scraper error: {e}")
        return []


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

    # Serve from cache if available (saves all Groq calls for repeated queries)
    cached = _cache.get(request.query)
    if cached:
        return cached

    # 1. Parse natural language query into filters
    filters = await parse_query(request.query)
    logger.info(f"Filters: {filters}")

    # 2. Scrape both sources + fetch model info in parallel
    async def _get_model_info():
        make = filters.get("make", "")
        model = filters.get("model_name", "")
        if make:
            # Use model name if known, otherwise get brand-level overview
            return await generate_model_info(make, model or make)
        return {}

    pw_cars, olx_cars, model_info = await asyncio.gather(
        _scrape_pakwheels(filters),
        _scrape_olx(filters),
        _get_model_info(),
    )
    logger.info(f"Combined: PW={len(pw_cars)} OLX={len(olx_cars)}")

    raw_cars = pw_cars + olx_cars
    source = "live"

    # No listings found — return immediately without caching so next search retries live
    if not raw_cars:
        logger.warning("Both scrapers returned 0 results")
        return SearchResponse(
            query=request.query,
            filters=filters,
            cars=[],
            total_found=0,
            ai_summary="No listings found for your search. Try a different city, remove filters, or check the spelling.",
            model_info=model_info,
            source="live",
        )

    # 3. Rank all cars by relevance
    ranked = rank_cars(raw_cars, filters)

    # 3b. Hard filter: when a specific model is requested, only keep cars whose
    # title contains that model keyword. This eliminates wrong-model results
    # (e.g. Wagon R / Mehran / Land Cruiser when searching for Cultus) regardless
    # of how many incidental bonuses (year, city) they accrue.
    if filters.get("model_name"):
        model_kw = filters["model_name"].lower()
        model_matched = [c for c in ranked if model_kw in (c.get("title") or "").lower()]
        if len(model_matched) >= 2:
            ranked = model_matched

    # 3c. Soft filter: drop wrong-brand cars when make is specified.
    # If fewer than 2 correct-brand cars survive, return empty rather than showing wrong makes.
    if filters.get("make"):
        relevant = [c for c in ranked if c.get("score", 0) >= 0]
        ranked = relevant if relevant else []

    logger.info(f"After relevance filter: {len(ranked)} cars")

    # 4. Pick top N for AI explanations, ensuring both sources are represented
    pw_ranked  = [c for c in ranked if c.get("source") == "pakwheels"]
    olx_ranked = [c for c in ranked if c.get("source") == "olx"]

    if pw_ranked and olx_ranked:
        # Reserve 3 OLX slots so OLX always appears in recommended
        top_olx = olx_ranked[:3]
        top_pw  = pw_ranked[:TOP_CARS_FOR_AI - len(top_olx)]
        top_10  = sorted(top_pw + top_olx, key=lambda c: c.get("score", 0), reverse=True)
    else:
        top_10 = ranked[:TOP_CARS_FOR_AI]

    # Mark top_10 as recommended before AI (so tab works even if AI fails)
    for car in top_10:
        car["is_recommended"] = True

    # 5. Generate AI explanations as ordered list (avoids title-key mismatch)
    explanations = await generate_explanations(request.query, top_10, filters)
    logger.info(f"Explanations: got {len(explanations)} for {len(top_10)} cars")
    for i, car in enumerate(top_10):
        expl = explanations[i] if i < len(explanations) else ""
        car["ai_explanation"] = expl if (isinstance(expl, str) and expl.strip()) else ""
        if i < 3:
            logger.info(f"  Car {i+1} ai_explanation set: {repr(car['ai_explanation'][:80]) if car['ai_explanation'] else 'EMPTY'}")

    # 5b. Vision AI: assess car condition — max 2 concurrent to avoid Groq rate limits
    _vision_sem = asyncio.Semaphore(2)

    async def _vision_for(car: dict) -> Optional[str]:
        imgs = car.get("images") or ([car["image"]] if car.get("image") else [])
        if not imgs:
            return None
        async with _vision_sem:
            return await analyze_car_image(imgs[:2], car["title"], car.get("source", "pakwheels"))

    vision_cars = top_10[:TOP_CARS_FOR_VISION]
    try:
        condition_results = await asyncio.wait_for(
            asyncio.gather(*[_vision_for(c) for c in vision_cars], return_exceptions=True),
            timeout=50,
        )
    except asyncio.TimeoutError:
        logger.warning("Vision analysis timed out — skipping remaining")
        condition_results = []
    for car, note in zip(vision_cars, condition_results):
        if isinstance(note, str) and note:
            car["condition_note"] = note

    # 6. Generate AI summary
    ai_summary = await generate_summary(request.query, top_10, filters)

    # 7. Return ALL cars — top 10 first (with AI), then remaining by score
    top_10_urls = {c.get("url") for c in top_10}
    remaining = [c for c in ranked if c.get("url") not in top_10_urls]
    all_cars_ordered = top_10 + remaining

    car_listings = []
    for car in all_cars_ordered:
        try:
            car_listings.append(CarListing(**car))
        except Exception as e:
            logger.debug(f"Skipping invalid car: {e}")

    response = SearchResponse(
        query=request.query,
        filters=filters,
        cars=car_listings,
        total_found=len(ranked),
        ai_summary=ai_summary,
        model_info=model_info,
        source=source,
    )
    # Only cache real results — empty results are not cached so next search retries live
    if car_listings:
        _cache.set(request.query, response)
    return response
