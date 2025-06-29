from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import uvicorn
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def read_root():
    return {"message": "Amazon Scraper API is running!"}


@app.get("/scrape")
async def scrape_amazon(query: str = Query(..., description="Search term")):
    search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
    affiliate_tag = "kouki0714-20"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ))
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
                # Title
                title_el = await product.query_selector("h2 span")
                title = await title_el.inner_text() if title_el else None

                # Price
                price_el = await product.query_selector("span.a-price")
                if price_el:
                    price_whole = await price_el.query_selector("span.a-price-whole")
                    price_frac = await price_el.query_selector("span.a-price-fraction")
                    price = f"${(await price_whole.inner_text()).replace(',', '')}.{await price_frac.inner_text()}" \
                        if price_whole and price_frac else None
                else:
                    price = None

                # Rating
                rating_el = await product.query_selector("span.a-icon-alt")
                rating = (await rating_el.inner_text()).split(" ")[0] if rating_el else None

                # High-quality Image
                img_el = await product.query_selector("img.s-image")
                img_url = None
                if img_el:
                    img_url = await img_el.get_attribute("data-src") or \
                              await img_el.get_attribute("srcset") or \
                              await img_el.get_attribute("src")
                    if img_url and "," in img_url:  # pick last (highest-res) in srcset
                        img_url = img_url.split(",")[-1].strip().split(" ")[0]

                # URL with Affiliate Tag
                link_el = await product.query_selector("a.a-link-normal.s-underline-text")
                if not link_el:
                    link_el = await product.query_selector("a")
                href = await link_el.get_attribute("href") if link_el else None
                product_url = None
                if href and href.startswith("/"):
                    base_url = f"https://www.amazon.com{href}"
                    product_url = base_url.split("?")[0] + f"?tag={affiliate_tag}"

                if title and product_url:
                    result.append({
                        "asin": asin,
                        "product_title": title,
                        "product_price": price,
                        "product_star_rating": rating,
                        "product_url": product_url,
                        "product_photo": img_url,
                        "currency": "USD",
                        "is_prime": False,
                        "is_amazon_choice": False,
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
