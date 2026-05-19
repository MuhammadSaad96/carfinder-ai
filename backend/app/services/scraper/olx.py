"""
OLX Pakistan scraper.
OLX is a React SPA — requires Playwright.
Uses aria-label for specs (Year/Mileage/FuelType still stable),
link[title] for car title, and span text-match for price.
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

OLX_CITY_SLUGS = {
    "islamabad": "islamabad_c6",
    "rawalpindi": "rawalpindi_c68",
    "lahore": "lahore_c7",
    "karachi": "karachi_c8",
    "faisalabad": "faisalabad_c69",
    "multan": "multan_c78",
    "peshawar": "peshawar_c10",
    "quetta": "quetta_c74",
}


class OLXScraper:
    BASE_URL = "https://www.olx.com.pk"
    CARS_PATH = "/cars_c84/"
    # /items/q-{query}/ returns keyword-matched results.
    # /cars_c84/?q= ignores keywords and shows sponsored junk.
    SEARCH_PATH = "/items/"

    def build_url(self, filters: dict) -> str:
        city = (filters.get("city") or "").strip().lower()

        # Build car-specific search terms first (make + model)
        car_parts = []
        if filters.get("make"):
            car_parts.append(filters["make"].strip().lower())
        if filters.get("model_name"):
            car_parts.append(filters["model_name"].strip().lower())

        # Fallback: use first 2 words of search_keywords if no make/model
        # (never use city alone — that returns ALL of OLX in that city)
        if not car_parts and filters.get("search_keywords"):
            kw_words = (filters["search_keywords"] or "").split()[:2]
            if kw_words:
                car_parts.append(" ".join(kw_words))

        if car_parts:
            if city:
                car_parts.append(city)
            query = "-".join(p.replace(" ", "-") for p in car_parts)
            url = f"{self.BASE_URL}{self.SEARCH_PATH}q-{query}/"
        else:
            # No car terms at all — fall back to cars category browse
            url = f"{self.BASE_URL}{self.CARS_PATH}"

        logger.info(f"OLX URL: {url}")
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
        return f"PKR {int(lacs)} Lacs" if lacs == int(lacs) else f"PKR {lacs:.2f} Lacs"

    def _extract_city(self, location_text: str) -> Optional[str]:
        if not location_text:
            return None
        parts = [p.strip() for p in location_text.split(",")]
        return parts[-1] if parts else location_text.split("-")[0].strip()

    def _infer_transmission(self, title: str) -> Optional[str]:
        t = (title or "").lower()
        if "automatic" in t or " auto " in t:
            return "Automatic"
        if "manual" in t:
            return "Manual"
        return None

    def _parse_article(self, article) -> Optional[dict]:
        try:
            # URL + title: from <a href="/item/..."> title attribute (stable)
            link = article.find("a", href=re.compile(r"/item/"), attrs={"title": True})
            if not link:
                link = article.find("a", href=re.compile(r"/item/"))
            url = (self.BASE_URL + link["href"]) if link and link.get("href") else ""

            title = None
            if link and link.get("title"):
                title = link["title"].strip()
            if not title:
                h2 = article.find("h2")
                title = h2.get_text(strip=True) if h2 else None
            if not title or len(title) < 4:
                return None

            # Price: first span whose text starts with "Rs"
            price_text = ""
            for span in article.find_all("span"):
                t = span.get_text(strip=True)
                if t.startswith("Rs ") and len(t) < 35:
                    price_text = t
                    break
            price = self._parse_price(price_text)

            # Year, Mileage, FuelType — aria-labels are stable across CSS rebuilds
            year_el = article.find(attrs={"aria-label": "Year"})
            year = None
            if year_el:
                m = re.search(r"20\d{2}|19\d{2}", year_el.get_text())
                year = int(m.group()) if m else None

            mileage_el = article.find(attrs={"aria-label": "Mileage"})
            mileage_display = mileage = None
            if mileage_el:
                mileage_display = mileage_el.get_text(strip=True)
                nums = re.findall(r"[\d,]+", mileage_display)
                mileage = int(nums[0].replace(",", "")) if nums else None

            fuel_el = article.find(attrs={"aria-label": "FuelType"})
            fuel_type = fuel_el.get_text(strip=True) if fuel_el else None

            transmission = self._infer_transmission(title)

            # Location: the span just before the "Creation date" element
            city = None
            date_el = article.find(attrs={"aria-label": "Creation date"})
            if date_el:
                try:
                    # date_el → <span aria-label="Creation date">
                    # parent → wrapper span, parent.parent → location row container
                    row = date_el.parent.parent
                    for span in row.find_all("span"):
                        if span.get("aria-label"):
                            continue
                        t = span.get_text(strip=True)
                        if t and t != "•" and "ago" not in t and len(t) > 3 and not t.startswith("Rs"):
                            city = self._extract_city(t)
                            if city:
                                break
                except Exception:
                    city = None

            # Images: collect all OLX CDN images in this article, upgrade thumbnail resolution
            seen_srcs: set = set()
            images = []
            for img_tag in article.find_all("img", src=re.compile(r"images\.olx\.com\.pk")):
                src = img_tag.get("src") or img_tag.get("data-src")
                if not src or src in seen_srcs:
                    continue
                # Upgrade small thumbnail sizes to 400x300
                src = re.sub(r'_\d+x\d+\.', '_400x300.', src)
                images.append(src)
                seen_srcs.add(src)
            # Also check lazy-load data-src attrs
            for img_tag in article.find_all("img", attrs={"data-src": re.compile(r"images\.olx\.com\.pk")}):
                src = img_tag.get("data-src")
                if not src or src in seen_srcs:
                    continue
                src = re.sub(r'_\d+x\d+\.', '_400x300.', src)
                images.append(src)
                seen_srcs.add(src)
            image = images[0] if images else None

            price_display = self._format_price(price) if price else price_text or "Price N/A"

            return {
                "title": title,
                "price": price,
                "price_display": price_display,
                "city": city,
                "year": year,
                "mileage": mileage,
                "mileage_display": mileage_display,
                "transmission": transmission,
                "fuel_type": fuel_type,
                "image": image,
                "images": images,
                "url": url,
                "source": "olx",
                "score": 0,
                "ai_explanation": None,
                "condition_note": None,
            }
        except Exception as e:
            logger.debug(f"OLX parse error: {e}")
            return None

    async def _fetch_listing_images(self, url: str, existing: list) -> list:
        """Try to get all images from individual OLX listing page via httpx."""
        if not url:
            return existing
        import httpx as _httpx, json as _json
        try:
            async with _httpx.AsyncClient(
                timeout=12,
                headers={"User-Agent": HEADERS_UA, "Referer": "https://www.olx.com.pk/"},
                follow_redirects=True,
            ) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    return existing
                html = r.text
            from bs4 import BeautifulSoup as _BS
            soup = _BS(html, "lxml")
            # OLX embeds full data in __NEXT_DATA__ script tag
            nd = soup.find("script", id="__NEXT_DATA__")
            if nd and nd.string:
                try:
                    data = _json.loads(nd.string)
                    photos = (
                        data.get("props", {}).get("pageProps", {})
                            .get("ad", {}).get("photos", [])
                        or
                        data.get("props", {}).get("pageProps", {})
                            .get("listing", {}).get("photos", [])
                    )
                    urls = []
                    for p in photos:
                        if isinstance(p, dict):
                            src = p.get("url") or p.get("src") or p.get("link") or ""
                        else:
                            src = str(p)
                        if src and src not in urls:
                            urls.append(src)
                    if urls:
                        return urls
                except Exception:
                    pass
            # Fallback: OLX CDN images in rendered HTML
            imgs = []
            for img in soup.find_all("img", src=re.compile(r"images\.olx\.com\.pk")):
                src = img.get("src")
                if src and src not in imgs:
                    src = re.sub(r'_\d+x\d+\.', '_400x300.', src)
                    imgs.append(src)
            return imgs if imgs else existing
        except Exception as e:
            logger.debug(f"OLX image fetch failed for {url}: {e}")
            return existing

    async def _enrich_images(self, cars: list) -> list:
        """Enrich each car with all images from its individual listing page."""
        sem = asyncio.Semaphore(4)

        async def _enrich(car):
            async with sem:
                imgs = await self._fetch_listing_images(car.get("url", ""), car.get("images", []))
                car["images"] = imgs
                if imgs:
                    car["image"] = imgs[0]
            return car

        return list(await asyncio.gather(*[_enrich(c) for c in cars]))

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
                await page.wait_for_timeout(1500)
                html = await page.content()
                await browser.close()

            soup = BeautifulSoup(html, "lxml")
            articles = soup.find_all("article")
            logger.info(f"OLX: found {len(articles)} articles")

            cars = []
            for art in articles[:max_results]:
                car = self._parse_article(art)
                if car:
                    cars.append(car)

            logger.info(f"OLX: parsed {len(cars)} cars")
            cars = await self._enrich_images(cars)
            return cars

        except Exception as e:
            logger.error(f"OLX scrape failed: {e}")
            return []
