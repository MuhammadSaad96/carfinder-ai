import json
import logging
import asyncio
from typing import Optional
from groq import Groq
from app.config import GROQ_API_KEY, GROQ_MODEL, GROQ_VISION_MODEL

logger = logging.getLogger(__name__)

_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


PARSE_QUERY_SYSTEM = """You are an expert at understanding Pakistani car buyer queries.
Extract structured search filters from natural language queries.
The query might be in English, Urdu, Roman Urdu, or a mix — including typos.

Common Pakistani terms:
- "lakh/lac" = 100,000 PKR  (e.g. "20 lakh" = 2,000,000 PKR)
- "gari/gaari/car" = car
- "main/mein" = in (location indicator)
- "chahiye/chahiay" = want/need
- "tak" = up to / maximum
- "se" = from / minimum
- "automatic/auto" = automatic transmission
- Cities: Islamabad, Rawalpindi, Lahore, Karachi, Faisalabad, Multan, Peshawar, Quetta

Common typos / Pakistani spellings to recognise:
- "haval jolion", "jolion" → model_name: "jolion", make: "haval"
- "haval h6", "h6" → model_name: "h6", make: "haval"
- "haval dargo", "dargo" → model_name: "dargo", make: "haval"
- "wangon r", "wagonr", "vagon r", "wagon", "wango" → model_name: "wagon r", make: "suzuki"
- "corola", "corrolla" → model_name: "corolla", make: "toyota"
- "civick", "covic" → model_name: "civic", make: "honda"
- "alto", "mehran", "cultus", "swift", "bolan", "ravi" → make: "suzuki"
- "sportage", "picanto", "stonic", "sorento" → make: "kia"
- "elantra", "tucson", "santro", "sonata" → make: "hyundai"
- "yaris", "passo", "vitz", "corolla", "fortuner", "hilux", "land cruiser" → make: "toyota"
- "haval", "jolion", "h6", "dargo" → make: "haval"
- "changan", "alsvin", "karvaan" → make: "changan"
- "mg", "hs", "zs" → make: "mg"
- "proton", "saga", "x70" → make: "proton"

IMPORTANT rules:
- Colors (red, white, black, silver, grey…) are NOT search_keywords — ignore them completely.
- Condition words (new, old, used, urgent) are NOT search_keywords — ignore them.
- search_keywords should contain ONLY car-relevant terms not already captured in make/model_name.
- If you recognise the car make/model, always set make and model_name — don't leave them null.

Return ONLY valid JSON with these exact fields (use null for anything not mentioned):
{
  "max_price": <integer in PKR or null>,
  "min_price": <integer in PKR or null>,
  "city": <exact city name or null>,
  "transmission": <"automatic" or "manual" or null>,
  "fuel_type": <"petrol" or "diesel" or "hybrid" or "electric" or "cng" or null>,
  "max_mileage": <integer km or null>,
  "min_year": <4-digit year integer or null>,
  "make": <car brand lowercase or null>,
  "model_name": <car model lowercase or null>,
  "search_keywords": <2-3 key car-relevant search terms or null>
}"""


async def parse_query(query: str) -> dict:
    def _call():
        client = get_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": PARSE_QUERY_SYSTEM},
                {"role": "user", "content": f"Query: {query}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=400,
        )
        return json.loads(response.choices[0].message.content)

    try:
        result = await asyncio.to_thread(_call)
        return {k: v for k, v in result.items() if v is not None}
    except Exception as e:
        logger.error(f"Groq parse_query error: {e}")
        return {}


EXPLANATION_SYSTEM = """You are a sharp, experienced Pakistani car market analyst helping buyers make smart decisions.
For each car write exactly 2 specific, honest sentences:
  Sentence 1 — Price verdict: is it below market average (good deal), near average (fair price), or above average (overpriced)? Reference the % context given.
  Sentence 2 — Key insight: comment on the km/year usage (very low / good / normal / high), the car's age and condition implication, or one concrete thing a buyer should verify.
Be direct and specific — avoid vague praise. Never invent numbers. Use ONLY the data provided."""


async def generate_explanations(query: str, cars: list, filters: dict) -> list:
    """Returns ordered list of explanations matching the cars input order."""
    if not cars:
        return []

    from datetime import date
    current_year = date.today().year

    # Compute average price so AI can give deal-quality context
    prices = [c.get("price") for c in cars if c.get("price") and isinstance(c.get("price"), (int, float))]
    avg_price = int(sum(prices) / len(prices)) if prices else 0

    car_lines = []
    for i, c in enumerate(cars):
        price = c.get("price") or 0
        price_ctx = ""
        if avg_price and price:
            pct = ((price - avg_price) / avg_price) * 100
            if pct < -8:
                price_ctx = f"[{abs(pct):.0f}% below avg — good deal]"
            elif pct > 8:
                price_ctx = f"[{pct:.0f}% above avg — premium priced]"
            else:
                price_ctx = "[near market average]"

        mileage_ctx = ""
        year = c.get("year")
        mileage = c.get("mileage")
        if year and mileage:
            age = max(current_year - int(year), 1)
            km_yr = int(mileage) / age
            if km_yr < 7_000:
                mileage_ctx = f"[{km_yr:,.0f} km/yr — very low usage]"
            elif km_yr < 12_000:
                mileage_ctx = f"[{km_yr:,.0f} km/yr — good usage]"
            elif km_yr < 18_000:
                mileage_ctx = f"[{km_yr:,.0f} km/yr — normal usage]"
            else:
                mileage_ctx = f"[{km_yr:,.0f} km/yr — high usage]"

        car_lines.append(
            f"{i+1}. {c.get('title')} | {c.get('price_display','N/A')} {price_ctx} | "
            f"mileage={c.get('mileage_display','N/A')} {mileage_ctx} | "
            f"year={c.get('year','N/A')} | city={c.get('city','N/A')} | "
            f"transmission={c.get('transmission','N/A')}"
        )

    active_filters = {k: v for k, v in filters.items() if v}
    avg_display = f"PKR {avg_price/100_000:.1f} Lacs" if avg_price else "N/A"
    prompt = f"""Buyer searching for: "{query}"
Filters: {json.dumps(active_filters)}
Market average price across these results: {avg_display}

Cars to analyse (use ONLY these numbers — never invent data):
{chr(10).join(car_lines)}

Write exactly 2 honest, specific sentences per car using the price and mileage context shown.
Return JSON: {{"explanations": ["explanation for car 1", "explanation for car 2", ...]}}
Array must have exactly {len(cars)} items in the same order as above."""

    def _call():
        client = get_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": EXPLANATION_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1500,
        )
        result = json.loads(response.choices[0].message.content)
        # Robust extraction: handle {"explanations": [...]} or bare list values
        if "explanations" in result and isinstance(result["explanations"], list):
            return result["explanations"]
        # Fall back: return dict values in order if Groq used a different wrapper key
        for v in result.values():
            if isinstance(v, list):
                return v
        return []

    try:
        return await asyncio.to_thread(_call)
    except Exception as e:
        logger.error(f"Groq generate_explanations error: {e}")
        return []


MODEL_INFO_SYSTEM = """You are an expert on the Pakistani new and used car market.
Given a car make (and optionally a specific model), return structured facts for Pakistani buyers.
If only a brand is given (make = model), return general brand-level facts covering popular models.
Use Pakistan-specific context: PKR prices, local fuel averages, Pakistani variants.

Return ONLY valid JSON with exactly these fields (use null for anything genuinely unknown):
{
  "new_price": "<price range of popular new variants in PKR Lacs, e.g. '85–140 Lacs (H6/Jolion)'>",
  "fuel_average": "<city and highway economy, e.g. '12–14 km/l city · 15–17 km/l highway'>",
  "engine": "<engine options sold in Pakistan, e.g. '1.5T Petrol / 1.5T PHEV'>",
  "variants": ["<popular variant or model 1>", "<popular variant or model 2>"],
  "known_for": "<one punchy sentence: why Pakistani buyers choose this brand/model>",
  "check_before_buy": "<one specific thing buyers must inspect on this brand/model in Pakistan>"
}"""


async def generate_model_info(make: str, model_name: str) -> dict:
    """Return brand/model-level facts (new price, fuel avg, engine, variants) for the searched car."""
    subject = f"{make} {model_name}" if model_name.lower() != make.lower() else make
    def _call():
        client = get_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": MODEL_INFO_SYSTEM},
                {"role": "user", "content": f"Car: {subject}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=300,
        )
        return json.loads(response.choices[0].message.content)

    try:
        result = await asyncio.to_thread(_call)
        return {k: v for k, v in result.items() if v is not None}
    except Exception as e:
        logger.error(f"Groq model_info error: {e}")
        return {}


async def generate_summary(query: str, cars: list, filters: dict) -> str:
    if not cars:
        return "No cars found. Try broadening your search."

    def _call():
        client = get_client()
        top = cars[0]
        prompt = (
            f'User searched: "{query}"\n'
            f"Found {len(cars)} matching cars.\n"
            f"Best match: {top.get('title')} at {top.get('price_display', 'N/A')}\n\n"
            "Write 1-2 friendly English sentences summarizing the results. "
            "Be encouraging and helpful."
        )
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a friendly AI car advisor for Pakistani buyers. Respond in English."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=120,
        )
        return response.choices[0].message.content.strip()

    try:
        return await asyncio.to_thread(_call)
    except Exception as e:
        logger.error(f"Groq generate_summary error: {e}")
        return f"{len(cars)} cars found matching your search."


async def analyze_car_image(image_urls: list, car_title: str, source: str = "pakwheels") -> Optional[str]:
    """Download up to 4 car images and assess visible condition using Groq vision model."""
    import httpx
    import base64

    if not image_urls:
        return None

    referer = "https://www.pakwheels.com/" if source == "pakwheels" else "https://www.olx.com.pk/"

    async def _download(url: str):
        try:
            async with httpx.AsyncClient(timeout=12, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": referer,
            }) as client:
                resp = await client.get(url)
                if resp.status_code != 200 or not resp.content:
                    return None
                data = base64.b64encode(resp.content).decode("utf-8")
                ct = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                mime = "image/png" if "png" in ct else "image/webp" if "webp" in ct else "image/jpeg"
                return {"data": data, "mime": mime}
        except Exception:
            return None

    # Download up to 4 images concurrently
    downloaded = await asyncio.gather(*[_download(url) for url in image_urls[:4]])
    images = [r for r in downloaded if r is not None]

    if not images:
        logger.warning(f"Vision: no images downloaded for {car_title}")
        return None

    # Build multi-image content — all photos first, then the instruction
    content = []
    for img in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{img['mime']};base64,{img['data']}"},
        })
    content.append({
        "type": "text",
        "text": (
            f"These are {len(images)} listing photo(s) of a {car_title} for sale in Pakistan. "
            "Photos may show exterior angles, interior, and engine bay.\n"
            "Assess visible condition to help a buyer. "
            "Reply in EXACTLY this format (no extra text):\n\n"
            "Overall: [Excellent / Good / Fair / Poor]\n"
            "• Paint: [state the color; note finish quality, any scratches, fade, oxidation, or touch-up spots]\n"
            "• Body: [panels, dents, rust, alignment — be specific even about minor issues]\n"
            "• Cleanliness: [exterior wash quality and overall presentation]\n"
            "• Interior: [describe seats, dashboard, steering wheel condition from interior photos; "
            "write 'Not visible' ONLY if no interior shot exists in these photos]\n"
            "• Verdict: [one specific, actionable tip for the buyer]\n\n"
            "Be honest and specific. Name the color. Call out any defects you see. "
            "Avoid generic phrases like 'appears clean' unless it genuinely stands out."
        ),
    })

    def _call():
        client = get_client()
        response = client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[{"role": "user", "content": content}],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    try:
        return await asyncio.to_thread(_call)
    except Exception as e:
        logger.error(f"Groq vision error for {car_title}: {e}")
        return None
