import logging
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.routes import search, parse_query

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="CarFinder AI",
    description="AI-powered car discovery for the Pakistani market",
    version="1.0.0",
)

import os
_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(parse_query.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "CarFinder AI"}


@app.get("/proxy-image")
async def proxy_image(url: str):
    """Proxy car images to fix hotlink protection on PakWheels & OLX CDNs."""
    if not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid URL")

    referer = (
        "https://www.pakwheels.com/"
        if "pakwheels" in url
        else "https://www.olx.com.pk/"
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": referer,
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                },
                follow_redirects=True,
            )
        if r.status_code != 200:
            raise HTTPException(status_code=404, detail="Image not found")

        content_type = r.headers.get("content-type", "image/jpeg")
        return Response(
            content=r.content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image fetch timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
