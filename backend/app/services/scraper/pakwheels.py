"""
PakWheels scraper — uses JSON-LD structured data embedded in each listing.
Each <li.classified-listing> contains a <script type="application/ld+json"> with
clean, machine-readable car data. No fragile CSS selector parsing needed.
"""

import re
import json
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

CITY_SLUGS = {
    "islamabad": "islamabad", "rawalpindi": "rawalpindi", "lahore": "lahore",
    "karachi": "karachi", "faisalabad": "faisalabad", "multan": "multan",
    "peshawar": "peshawar", "quetta": "quetta", "sialkot": "sialkot",
    "gujranwala": "gujranwala",
}

MAKE_SLUGS = {
    "honda": "honda", "toyota": "toyota", "suzuki": "suzuki", "kia": "kia",
    "hyundai": "hyundai", "changan": "changan", "mg": "mg", "proton": "proton",
    "nissan": "nissan", "mitsubishi": "mitsubishi", "daihatsu": "daihatsu",
    "mercedes": "mercedes-benz", "bmw": "bmw", "audi": "audi", "peugeot": "peugeot",
    "haval": "haval", "gwm": "haval", "revo": "toyota", "fortuner": "toyota",
    "land rover": "land-rover", "range rover": "land-rover",
    "isuzu": "isuzu", "faw": "faw", "dfsk": "dfsk", "prince": "prince",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}

STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    window.chrome = { runtime: {} };
"""


class PakWheelsScraper:
    BASE_URL = "https://www.pakwheels.com/used-cars/search/-/"

    # ------------------------------------------------------------------ #
    #  URL builder                                                         #
    # ------------------------------------------------------------------ #

    def build_url(self, filters: dict) -> str:
        slug_parts = []

        city = (filters.get("city") or "").lower().strip()
        if city:
            slug_parts.append(f"ct_{CITY_SLUGS.get(city, city.replace(' ', '-'))}")

        transmission = (filters.get("transmission") or "").lower()
        if "auto" in transmission:
            slug_parts.append("tr_automatic")
        elif "manual" in transmission:
            slug_parts.append("tr_manual")

        make = (filters.get("make") or "").lower().strip()
        if make:
            slug_parts.append(f"mk_{MAKE_SLUGS.get(make, make.replace(' ', '-'))}")

        fuel = (filters.get("fuel_type") or "").lower()
        fuel_map = {"petrol": "petrol", "diesel": "diesel", "hybrid": "hybrid",
                    "electric": "electric", "cng": "cng"}
        if fuel in fuel_map:
            slug_parts.append(f"fu_{fuel_map[fuel]}")

        url = self.BASE_URL + ("/".join(slug_parts) + "/" if slug_parts else "")

        params = []
        if filters.get("max_price"):
            params.append(f"price_max={filters['max_price']}")
        if filters.get("min_price"):
            params.append(f"price_min={filters['min_price']}")
        if filters.get("max_mileage"):
            params.append(f"mileage_max={filters['max_mileage']}")
        if filters.get("min_year"):
            params.append(f"year_from={filters['min_year']}")

        # Use model_name only — search_keywords may contain colors/descriptors that break PakWheels search
        kw = filters.get("model_name") or ""
        if kw:
            params.append(f"q={kw.replace(' ', '+')}")

        if params:
            url += "?" + "&".join(params)

        logger.info(f"Built URL: {url}")
        return url

    # ------------------------------------------------------------------ #
    #  Fetching                                                            #
    # ------------------------------------------------------------------ #

    async def _fetch_httpx(self, url: str) -> Optional[str]:
        try:
            import httpx
            async with httpx.AsyncClient(
                headers=HEADERS, follow_redirects=True, timeout=25
            ) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    logger.info(f"httpx OK — {len(r.text):,} bytes")
                    return r.text
                logger.warning(f"httpx status {r.status_code}")
        except Exception as e:
            logger.warning(f"httpx error: {e}")
        return None

    async def _fetch_playwright(self, url: str) -> Optional[str]:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--window-size=1366,768",
                    ],
                )
                ctx = await browser.new_context(
                    user_agent=HEADERS["User-Agent"],
                    viewport={"width": 1366, "height": 768},
                    locale="en-US",
                    timezone_id="Asia/Karachi",
                )
                await ctx.add_init_script(STEALTH_SCRIPT)
                page = await ctx.new_page()
                await page.goto(url, wait_until="networkidle", timeout=45_000)
                await page.wait_for_timeout(3000)
                html = await page.content()
                await browser.close()
                logger.info(f"Playwright OK — {len(html):,} bytes")
                return html
        except Exception as e:
            logger.error(f"Playwright error: {e}")
        return None

    # ------------------------------------------------------------------ #
    #  Multi-image enrichment — visit individual listing pages            #
    # ------------------------------------------------------------------ #

    async def _fetch_all_images(self, url: str, fallback: Optional[str] = None) -> list:
        """Fetch individual PakWheels listing page and return all gallery images."""
        if not url:
            return [fallback] if fallback else []
        try:
            html = await self._fetch_httpx(url)
            if not html:
                return [fallback] if fallback else []

            # Extract folder ID from the main image URL — all images for this listing
            # share the same /ad_pictures/{folder_id}/ path on the CDN.
            folder_id = None
            if fallback:
                m = re.search(r'/ad_pictures/(\d+)/', fallback)
                if m:
                    folder_id = m.group(1)

            if folder_id:
                # Collect all full-size CDN images in this folder (skip tn_ thumbnails and Slide_ dupes)
                pattern = (
                    rf'(https?://cache\d+\.pakwheels\.com/ad_pictures/{folder_id}/'
                    rf'(?!tn_)(?!Slide_)[^\s"\'<>]+)'
                )
                imgs = list(dict.fromkeys(re.findall(pattern, html)))
                if imgs:
                    return imgs

            # Fallback: JSON-LD image field
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            for script in soup.find_all("script", type="application/ld+json"):
                if not script.string:
                    continue
                try:
                    data = json.loads(script.string)
                    img_field = data.get("image")
                    if isinstance(img_field, list):
                        imgs = [i for i in img_field if isinstance(i, str) and i]
                        if imgs:
                            return imgs
                    elif isinstance(img_field, str) and img_field:
                        return [img_field]
                except Exception:
                    continue

            return [fallback] if fallback else []
        except Exception as e:
            logger.debug(f"PW image fetch failed for {url}: {e}")
            return [fallback] if fallback else []

    async def _enrich_images(self, cars: list) -> list:
        """Fetch all gallery images for each car in parallel (max 3 concurrent, 12s budget)."""
        sem = asyncio.Semaphore(3)

        async def _enrich(car):
            async with sem:
                try:
                    imgs = await asyncio.wait_for(
                        self._fetch_all_images(car.get("url"), car.get("image")),
                        timeout=12,
                    )
                    car["images"] = imgs
                    if imgs:
                        car["image"] = imgs[0]
                except asyncio.TimeoutError:
                    car["images"] = [car["image"]] if car.get("image") else []
            return car

        return list(await asyncio.gather(*[_enrich(c) for c in cars]))

    # ------------------------------------------------------------------ #
    #  Parsing — JSON-LD first, HTML fallback                             #
    # ------------------------------------------------------------------ #

    def _parse_mileage_str(self, text: str) -> Optional[int]:
        """'55,000 km' → 55000"""
        nums = re.findall(r"[\d,]+", text or "")
        return int(nums[0].replace(",", "")) if nums else None

    def _clean_title(self, name: str) -> str:
        """'Honda Civic 2024 for sale in Lahore' → 'Honda Civic 2024'"""
        return re.sub(r"\s+for sale in .+", "", name, flags=re.IGNORECASE).strip()

    def _format_price(self, price_int: int) -> str:
        lacs = price_int / 100_000
        if lacs == int(lacs):
            return f"PKR {int(lacs)} Lacs"
        return f"PKR {lacs:.1f} Lacs"

    def _parse_listing_jsonld(self, listing) -> Optional[dict]:
        """Extract car data from the JSON-LD script tag — most reliable method."""
        script = listing.find("script", type="application/ld+json")
        if not script or not script.string:
            return None
        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            return None

        offers = data.get("offers", {})
        raw_name = data.get("name", "")
        if not raw_name:
            return None

        title = self._clean_title(raw_name)
        price = offers.get("price")
        url = offers.get("url", "")
        year = data.get("modelDate")
        transmission = data.get("vehicleTransmission")
        fuel_type = data.get("fuelType")
        mileage_str = data.get("mileageFromOdometer", "")
        mileage = self._parse_mileage_str(mileage_str)
        image = data.get("image")

        # City from description ("Honda Civic 2024 for sale in Lahore")
        desc = data.get("description", "")
        city_match = re.search(r"for sale in (.+)", desc, re.IGNORECASE)
        city = city_match.group(1).strip() if city_match else None

        price_int = int(price) if price else None

        return {
            "title": title,
            "price": price_int,
            "price_display": self._format_price(price_int) if price_int else "Price N/A",
            "city": city,
            "year": int(year) if year else None,
            "mileage": mileage,
            "mileage_display": mileage_str or (f"{mileage:,} km" if mileage else None),
            "transmission": transmission,
            "fuel_type": fuel_type,
            "image": image,
            "images": [image] if image else [],
            "url": url,
            "score": 0,
            "ai_explanation": None,
            "condition_note": None,
        }

    def _extract_cars(self, html: str, max_results: int) -> list:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        listings = soup.select("li.classified-listing")
        logger.info(f"Found {len(listings)} listings on page")

        cars = []
        for listing in listings[:max_results]:
            car = self._parse_listing_jsonld(listing)
            if car and car.get("title"):
                cars.append(car)

        logger.info(f"Successfully parsed {len(cars)} cars")
        return cars

    # ------------------------------------------------------------------ #
    #  Public entry point                                                  #
    # ------------------------------------------------------------------ #

    async def scrape(self, filters: dict, max_results: int = 20) -> list:
        url = self.build_url(filters)

        # Try fast httpx first
        html = await self._fetch_httpx(url)
        if html:
            cars = self._extract_cars(html, max_results)
            if cars:
                return await self._enrich_images(cars)
            logger.info("httpx returned page but no listings — trying Playwright")

        # Fall back to full browser
        html = await self._fetch_playwright(url)
        if html:
            cars = self._extract_cars(html, max_results)
            if cars:
                return await self._enrich_images(cars)

        logger.warning("No listings found from either method")
        return []
