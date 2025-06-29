from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import uvicorn
import uuid
import re

app = FastAPI()

# Allow all origins (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/scrape")
async def scrape_amazon(query: str = Query(..., description="Search term")):
    search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        page = await context.new_page()

        await page.goto(search_url, timeout=60000)
        await page.wait_for_selector("div.s-main-slot")

        products = await page.query_selector_all("div.s-main-slot > div[data-asin]")
        result = []

        for product in products:
            asin = await product.get_attribute("data-asin")
            if not asin:
                continue

            try:
                title = await product.query_selector("h2 span")
                title = await title.inner_text() if title else None

                price_whole = await product.query_selector("span.a-price-whole")
                price_frac = await product.query_selector("span.a-price-fraction")
                price = f"${(await price_whole.inner_text()).strip()}.{(await price_frac.inner_text()).strip()}" if price_whole and price_frac else None

                rating = await product.query_selector("span.a-icon-alt")
                rating = (await rating.inner_text()).split(" ")[0] if rating else None

                img = await product.query_selector("img.s-image")
                img_url = await img.get_attribute("src") if img else None

                link_tag = await product.query_selector("h2 a")
                href = await link_tag.get_attribute("href") if link_tag else ""
                product_url = f"https://www.amazon.com{href}" if href else ""

                result.append({
                    "asin": asin,
                    "product_title": title,
                    "product_price": price,
                    "product_star_rating": rating,
                    "product_url": product_url,
                    "product_photo": img_url,
                    "currency": "USD",
                    "is_prime": False,  # Skipped: requires extra selector
                    "is_amazon_choice": False,  # Skipped: optional
                    "sales_volume": None,
                    "product_badge": None,
                    "product_original_price": None,
                    "product_num_ratings": None
                })

            except Exception:
                continue

            if len(result) >= 10:
                break

        await browser.close()

    return {
        "status": "OK",
        "request_id": str(uuid.uuid4()),
        "parameters": {
            "query": query,
            "country": "US"
        },
        "data": {
            "products": result
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


