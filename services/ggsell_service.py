import asyncio
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from models.digiseller_models import BsProduct
from models.gg_sell_models import Button
from models.sheet_models import Payload
from utils.ggsell_utils import extract_json_from_html

HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/json',
    'origin': 'https://ggsel.net',
    'referer': 'https://ggsel.net/',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0'
}

GET_PRODS_URL = 'https://api4.ggsel.com/elastic/goods/categories'
PRODUCT_BASE_URL = 'https://ggsel.net/en/catalog/product/'
IMAGE_BASE_URL = "https://cdn.ggsel.com/images/"
PRICE_API_URL_TEMPLATE = "https://api4.ggsel.com/goods/{good_id}/price"
NUMBER_OF_PRODUCTS_TO_GET = 60


def _filter_products(products: List[BsProduct], payload: Payload) -> List[BsProduct]:
    filtered_products = []
    for product in products:
        if payload.include_keyword is not None:
            include_kws = payload.include_keyword.split(',')
            if not any(kw.strip().lower() in product.name.lower() for kw in include_kws):
                continue
        if payload.exclude_keyword is not None:
            exclude_kws = payload.exclude_keyword.split(',')
            if any(kw.strip().lower() in product.name.lower() for kw in exclude_kws):
                continue
        if int(product.sold_count) < payload.order_sold:
            continue
        filtered_products.append(product)

    return filtered_products


class GGSellService:
    """Service class to interact with the GGSel API asynchronously."""

    async def get_html_doc(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Asynchronously fetches the HTML content of a URL."""
        try:
            async with session.get(url, headers=HEADERS) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientError as e:
            print(f"Error fetching HTML from {url}: {e}")
            return None

    def get_id_section_from_html(self, html_doc: str) -> int:
        """Extracts the digi_catalog (id_section) from the page's initial data script."""
        soup = BeautifulSoup(html_doc, 'html.parser')
        try:
            extracted_data = extract_json_from_html(soup)
            # This path is more reliable for category pages
            id_section = extracted_data['props']['pageProps']['category']['digi_catalog']
            return int(id_section)
        except (KeyError, ValueError, TypeError) as e:
            print(f"Error parsing id_section from HTML: {e}")
            raise

    async def get_category_data(self, session: aiohttp.ClientSession, digi_catalog_id: int) -> List[dict]:
        """Asynchronously fetches product data for a given catalog ID."""
        payload = {
            "digi_catalog": digi_catalog_id, "limit": 60, "sort": "sortByPriceUp",
            "currency": "wmr", "lang": "en", "page": 1, "is_preorders": False,
            "with_filters": True, "search_after": [], "content_type_ids": [],
            "query_string": "", "with_forbidden": False, "min_price": "",
            "max_price": "", "platforms": []
        }
        try:
            async with session.post(GET_PRODS_URL, headers=HEADERS, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('data', {}).get('items', [])
        except aiohttp.ClientError as e:
            print(f"HTTP error occurred while fetching category data: {e}")
        return []

    def convert_to_bs_product(self, product_data: dict) -> BsProduct:
        """Converts a raw product dictionary into a BsProduct object."""
        sold_count = product_data.get('cnt_sell')
        return BsProduct(
            id=product_data.get('id_goods'),
            seller_name=product_data.get('seller_name'),
            name=product_data.get('name', 'N/A'),
            outside_price=str(product_data.get('price_wmr', '0.0')),
            sold_count=str(sold_count) if sold_count is not None else None,
            link=f"{PRODUCT_BASE_URL}{product_data.get('url', '')}",
        )

    def extract_buttons_from_html(self, html_content: str) -> List[Button]:
        """Extracts product option buttons from the product page HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        button_elements = soup.find_all('button', class_='MuiToggleButton-root')
        return [
            Button(id=btn.get('value'), name=btn.find('span').text.strip())
            for btn in button_elements if btn.get('value') and btn.find('span')
        ]

    def extract_option_id_from_html(self, html_doc: str) -> Optional[int]:
        soup = BeautifulSoup(html_doc, 'html.parser')
        try:
            data = extract_json_from_html(soup)

            options = data['props']['pageProps'].get('good', {}).get('options')
            if options is None:
                options = data['props']['pageProps'].get('productData', {}).get('options')

            if options:
                for option in options:
                    if option.get('type') == 'radio':
                        return option.get('id')
            else:
                pass
        except (KeyError, IndexError, TypeError) as e:
            print(f"Could not extract option_id for a product: {e}")
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(aiohttp.ClientError)
    )
    async def _fetch_price_for_button(self, session: aiohttp.ClientSession, good_id: int, option_id: int,
                                      button: Button):
        """Helper function to fetch price for a single button via GET request."""
        params = {"currency": "RUB", "unit_count": "1", f"options[{option_id}]": button.id}
        url = PRICE_API_URL_TEMPLATE.format(good_id=good_id)

        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                price = data.get("data", {}).get("amount")
                if price is not None:
                    button.price = float(price)
                else:
                    print(f"Warning: Price not found for button ID {button.id}")
        except aiohttp.ClientError as e:
            print(f"Request for button ID {button.id} failed. Tool will retry. Error: {e}")
            raise

    async def fulfill_button_data(self, session: aiohttp.ClientSession, bs_product: BsProduct) -> BsProduct:
        """Enriches a BsProduct's buttons with their prices from the API."""
        product_html = await self.get_html_doc(session, bs_product.link)
        if not product_html:
            return bs_product

        buttons = self.extract_buttons_from_html(product_html)
        option_id = self.extract_option_id_from_html(product_html)

        if not buttons or option_id is None:
            bs_product.list_button = buttons
            return bs_product

        tasks = [self._fetch_price_for_button(session, bs_product.id, option_id, button) for button in buttons]
        await asyncio.gather(*tasks)
        bs_product.list_button = buttons
        return bs_product

    async def fulfill_specific_button_data(self, session: aiohttp.ClientSession, bs_product: BsProduct,
                                           option_str: str) -> BsProduct:
        product_html = await self.get_html_doc(session, bs_product.link)
        if not product_html:
            return bs_product

        buttons = self.extract_buttons_from_html(product_html)
        if not option_str:
            bs_product.list_button = buttons
            return bs_product

        keys = [key.strip().lower() for key in option_str.split(',') if key.strip()]

        selected_buttons = [
            button for button in buttons
            if any(key in button.name.lower() for key in keys)
        ]

        if not selected_buttons:
            bs_product.list_button = []
            return bs_product
        option_id = self.extract_option_id_from_html(product_html)

        if not selected_buttons or option_id is None:
            bs_product.list_button = buttons
            return bs_product

        tasks = [self._fetch_price_for_button(session, bs_product.id, option_id, button) for button in selected_buttons]
        await asyncio.gather(*tasks)
        bs_product.list_button = selected_buttons
        bs_product.price = selected_buttons[0].price
        return bs_product

    async def get_list_products_for_processor(self, url: str) -> List[BsProduct]:
        """
        Main processor function to fetch a list of products and fulfill their details.
        Uses a semaphore to limit concurrency and avoid rate-limiting.
        """
        # Limit concurrency to 5 products at a time to avoid overwhelming the server
        semaphore = asyncio.Semaphore(5)

        async def fulfill_with_semaphore(session, product):
            """Wrapper to use the semaphore for each fulfillment task."""
            async with semaphore:
                # Add a small delay between batches to be safe
                await asyncio.sleep(1)
                return await self.fulfill_button_data(session, product)

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            html_doc = await self.get_html_doc(session, url)
            if not html_doc:
                return []

            id_sec = self.get_id_section_from_html(html_doc)
            products_raw = await self.get_category_data(session, id_sec)
            if not products_raw:
                return []

            products = [self.convert_to_bs_product(prod) for prod in products_raw]

            # Create concurrent tasks, managed by the semaphore
            tasks = [fulfill_with_semaphore(session, prod) for prod in products]

            # Run all fulfillment tasks concurrently and get the results
            fulfilled_products = await asyncio.gather(*tasks)

            return [p for p in fulfilled_products if p]  # Filter out None results if any

    async def fetch_product_list(self, session: aiohttp.ClientSession, url: str) -> List[BsProduct]:
        html_doc = await self.get_html_doc(session, url)
        if not html_doc:
            print("Can not fetch HTML document")
            return []

        id_sec = self.get_id_section_from_html(html_doc)
        products_raw = await self.get_category_data(session, id_sec)
        if not products_raw:
            print("Can not fetch product data from category")
            return []

        products = [self.convert_to_bs_product(prod) for prod in products_raw]
        return products

    async def fulfill_product_details(self, session: aiohttp.ClientSession, products: List[BsProduct]) -> List[
        BsProduct]:
        semaphore = asyncio.Semaphore(5)

        async def fulfill_with_semaphore(product: BsProduct):
            async with semaphore:
                await asyncio.sleep(1)
                return await self.fulfill_button_data(session, product)

        tasks = [fulfill_with_semaphore(prod) for prod in products]

        fulfilled_products = await asyncio.gather(*tasks)

        return [p for p in fulfilled_products if p]


    async def get_list_variants_products_for_processor(self, url: str, option_str: str, payload: Payload) -> List[BsProduct]:
        semaphore = asyncio.Semaphore(5)

        async def fulfill_with_semaphore(session, product):
            async with semaphore:
                # Add a small delay between batches to be safe
                await asyncio.sleep(1)
                return await self.fulfill_specific_button_data(session, product, option_str)

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            html_doc = await self.get_html_doc(session, url)
            if not html_doc:
                return []

            id_sec = self.get_id_section_from_html(html_doc)
            products_raw = await self.get_category_data(session, id_sec)
            if not products_raw:
                return []
            products = [self.convert_to_bs_product(prod) for prod in products_raw]

            _product_to_get = min(NUMBER_OF_PRODUCTS_TO_GET, len(products)) - 1

            products = products[:_product_to_get]
            filter_products = _filter_products(products, payload)
            tasks = [fulfill_with_semaphore(session, prod) for prod in filter_products]

            fulfilled_products = await asyncio.gather(*tasks)

            return [p for p in fulfilled_products if p]


async def main():
    """Main execution function."""
    service = GGSellService()
    category_url = "https://ggsel.net/en/catalog/nintendo-eshop-giftcards-us"

    print(f"--- Starting Processor for URL: {category_url} ---")

    # Single call to the main processor method
    list_of_products = await service.get_list_variants_products_for_processor(category_url, '10')

    print(f"\n--- ✅ Processing Complete. Found and processed {len(list_of_products)} products. ---")

    # Print details for a few products to verify
    for product in list_of_products:
        print(f"\nProduct: {product.name} (ID: {product.id})")
        if not product.list_button:
            print("  - No options/buttons found for this product.")
        if product.list_button:
            for button in product.list_button:
                price_str = f"${button.price:.2f}" if button.price is not None else "Price not available"
                print(f"  - Option: '{button.name}' (ID: {button.id}) -> Price: {price_str}")

# if __name__ == "__main__":
#     # Ensure you have the necessary libraries installed:
#     # pip install pydantic yarl aiohttp beautifulsoup4 tenacity
#     asyncio.run(main())
