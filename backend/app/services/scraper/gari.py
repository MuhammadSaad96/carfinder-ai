"""
Gari.pk scraper — Pakistan's dedicated used-car marketplace.
Uses Playwright (JavaScript-rendered SPA).
Listings live in div.block_ss containers; features are ordered div.div_feat children.
"""

import re
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

HEADERS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

MAKE_SLUGS = {
    "honda": "honda", "toyota": "toyota", "suzuki": "suzuki", "kia": "kia",
    "hyundai": "hyundai", "changan": "changan", "mg": "mg", "proton": "proton",
    "nissan": "nissan", "mitsubishi": "mitsubishi", "daihatsu": "daihatsu",
    "mercedes": "mercedes-benz", "bmw": "bmw", "audi": "audi",
}

MODEL_SLUGS = {
    "cultus": "cultus", "alto": "alto", "mehran": "mehran", "swift": "swift",
    "wagon r": "wagon-r", "civic": "civic", "city": "city", "hrv": "hrv",
    "corolla": "corolla", "yaris": "yaris", "passo": "passo", "vitz": "vitz",
    "sportage": "sportage", "picanto": "picanto", "stonic": "stonic",
    "elantra": "elantra", "tucson": "tucson", "mira": "mira", "move": "move",
}

CITY_SLUGS = {
    "islamabad": "islamabad", "rawalpindi": "rawalpindi", "lahore": "lahore",
    "karachi": "karachi", "faisalabad": "faisalabad", "multan": "multan",
    "peshawar": "peshawar", "quetta": "quetta",
}


class GariScraper:
    BASE_URL = "https://www.gari.pk"

    def build_url(self, filters: dict) -> str:
        make = (filters.get("make") or "").lower().strip()
        model = (filters.get("model_name") or "").lower().strip()
        city = (filters.get("city") or "").lower().strip()

        make_slug = MAKE_SLUGS.get(make, make.replace(" ", "-")) if make else ""
        model_slug = MODEL_SLUGS.get(model, model.replace(" ", "-")) if model else ""
        city_slug = CITY_SLUGS.get(city, city.replace(" ", "-")) if city else ""

        # Path: /used-cars/{city}-c/{make}/{model}/
        parts = ["used-cars"]
        if city_slug:
            parts.append(f"{city_slug}-c")
        if make_slug:
            parts.append(make_slug)
        if model_slug:
            parts.append(model_slug)

        url = f"{self.BASE_URL}/{'/'.join(parts)}/"

        # Append year filter if specified
        params = []
        if filters.get("min_year"):
            params.append(f"year_from={filters['min_year']}")
        if params:
            url += "?" + "&".join(params)

        logger.info(f"Gari URL: {url}")
        return url

    def _parse_price(self, text: str) -> Optional[int]:
        if not text:
            return None
        t = text.lower().strip()
        try:
            if "crore" in t:
                return int(float(re.findall(r"[\d.]+", t)[0]) * 10_000_000)
            if "lac" in t or "lakh" in t:
                return int(float(re.findall(r"[\d.]+", t)[0]) * 100_000)
            nums = re.sub(r"[^\d]", "", t)
            return int(nums) if nums else None
        except (IndexError, ValueError):
            return None

    def _format_price(self, p: int) -> str:
        lacs = p / 100_000
        return f"PKR {int(lacs)} Lacs" if lacs == int(lacs) else f"PKR {lacs:.1f} Lacs"

    def _parse_container(self, div) -> Optional[dict]:
        try:
            # Title + URL
            title_link = div.select_one("div#ad-title a")
            if not title_link:
                return None
            url = title_link.get("href", "")
            if not url.startswith("http"):
                url = self.BASE_URL + url
            title = title_link.get_text(strip=True)
            # Strip trailing "for Sale" / "for sale in ..."
            title = re.sub(r"\s+for sale.*$", "", title, flags=re.IGNORECASE).strip()
            if not title or len(title) < 4:
                return None

            # Image
            img_tag = div.select_one("div#image-cat img")
            image = img_tag.get("src") if img_tag else None

            # Features: div.div_feat children (index-based)
            feats = div.select("div#price-cat div.div_feat")
            feat_texts = [f.get_text(strip=True) for f in feats]

            year = None
            city = None
            mileage = None
            mileage_display = None
            price = None
            price_text = ""

            # Index 0: year
            if len(feat_texts) > 0:
                m = re.search(r"20\d{2}|19\d{2}", feat_texts[0])
                if m:
                    year = int(m.group())

            # Index 1: city
            if len(feat_texts) > 1:
                city = feat_texts[1].strip() or None

            # Index 2: mileage
            if len(feat_texts) > 2:
                raw = feat_texts[2]
                nums = re.findall(r"[\d,]+", raw)
                if nums:
                    mileage = int(nums[0].replace(",", ""))
                    mileage_display = raw.strip()

            # Price: find the bold inner div in index 3
            if len(feats) > 3:
                bold = feats[3].find(style=re.compile(r"font-weight\s*:\s*bold", re.I))
                if bold:
                    price_text = bold.get_text(strip=True)
                else:
                    price_text = feat_texts[3]
                price = self._parse_price(price_text)

            price_display = self._format_price(price) if price else price_text or "Price N/A"

            return {
                "title": title,
                "price": price,
                "price_display": price_display,
                "city": city,
                "year": year,
                "mileage": mileage,
                "mileage_display": mileage_display,
                "transmission": None,
                "fuel_type": None,
                "image": image,
                "images": [image] if image else [],
                "url": url,
                "source": "gari",
                "score": 0,
                "ai_explanation": None,
                "condition_note": None,
            }
        except Exception as e:
            logger.debug(f"Gari parse error: {e}")
            return None

    async def scrape(self, filters: dict, max_results: int = 15) -> list:
        url = self.build_url(filters)
        try:
            from playwright.async_api import async_playwright
            from bs4 import BeautifulSoup

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                )
                ctx = await browser.new_context(user_agent=HEADERS_UA)
                page = await ctx.new_page()
                await page.goto(url, wait_until="networkidle", timeout=45_000)
                await page.wait_for_timeout(2000)
                html = await page.content()
                await browser.close()

            soup = BeautifulSoup(html, "lxml")
            containers = soup.select("div.block_ss")
            logger.info(f"Gari: found {len(containers)} containers")

            cars = []
            for div in containers[:max_results]:
                car = self._parse_container(div)
                if car:
                    cars.append(car)

            logger.info(f"Gari: parsed {len(cars)} cars")
            return cars

        except Exception as e:
            logger.error(f"Gari scrape failed: {e}")
            return []
