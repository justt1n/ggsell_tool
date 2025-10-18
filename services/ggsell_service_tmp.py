import asyncio
from itertools import product

import aiohttp
from typing import List

import requests
from bs4 import BeautifulSoup

from models.digiseller_models import BsProduct
from models.gg_sell_models import Button
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
PRODUCT_BASE_URL = 'https://ggsel.net/en/catalog/'
IMAGE_BASE_URL = "https://cdn.ggsel.com/images/"
PRICE_API_URL_TEMPLATE = "https://api4.ggsel.com/goods/{good_id}/price"

class ggsell_service:
    def __init__(self):
        pass

    def get_id_section_from_html(self, url: str) -> int:
        html_str = requests.get(url)
        html_doc = html_str.text
        soup = BeautifulSoup(html_doc, 'html.parser')
        try:
            extracted_data = extract_json_from_html(soup)
            id_section = extracted_data[0]['props']['pageProps']['leaderProduct']['id_section']
        except KeyError:
            raise KeyError(
                "Could not find 'id_section' in the extracted JSON data."
            )
        return int(id_section)


    def get_category_data(self, digi_catalog_id: int) -> dict:
        payload = {
            "digi_catalog": digi_catalog_id,
            "limit": 60,
            "is_preorders": False,
            "with_filters": True,
            "search_after": [],
            "sort": "sortByPriceUp",
            "content_type_ids": [],
            "query_string": "",
            "with_forbidden": False,
            "min_price": "",
            "max_price": "",
            "currency": "wmz",
            "lang": "en",
            "platforms": [],
            "page": 1
        }

        try:
            response = requests.post(GET_PRODS_URL, headers=HEADERS, json=payload)
            response.raise_for_status()
            prod_list = response.json().get('data', {}).get('items', [])
            return prod_list
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"An error occurred: {err}")
        return {}

    def convert_to_BS_product(self, product_data: dict) -> BsProduct:
        sold_count = product_data.get('cnt_sell')
        sold_count_str = str(sold_count) if sold_count is not None else None

        product_url = f"{PRODUCT_BASE_URL}{product_data.get('url', '')}"
        product_id = product_url.split('/')[-1].split('-')[-1]
        return BsProduct(
            id=int(product_id),
            seller_name=product_data.get('seller_name'),
            name=product_data.get('name', 'N/A'),
            outside_price=product_data.get('price_wmz', '0.0'),
            sold_count=sold_count_str,
            link=product_url,
        )

    def extract_buttons_from_html(self, html_content: str) -> List[Button]:
        soup = BeautifulSoup(html_content, 'html.parser')

        button_elements = soup.find_all('button', class_='MuiToggleButton-root')

        extracted_buttons: List[Button] = []

        for button_element in button_elements:
            button_id = button_element.get('value')

            name_span = button_element.find('span')
            button_name = name_span.text.strip() if name_span else "N/A"

            if button_id and button_name != "N/A":
                extracted_buttons.append(
                    Button(id=button_id, name=button_name)
                )
        return extracted_buttons

    async def _fetch_price_for_button(self, session: aiohttp.ClientSession, good_id: int, option_id: int,
                                      button: Button):
        """
        Helper function to fetch price for a single button by sending a GET request.
        """
        # The API expects the options parameter formatted like: options[option_id]=button_id
        params = {
            "currency": "USD",
            "unit_count": "1",
            f"options[{option_id}]": button.id
        }

        # Format the URL with the specific good's ID
        url = PRICE_API_URL_TEMPLATE.format(good_id=good_id)

        try:
            # Use a GET request with the constructed params
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                price = data.get("data", {}).get("amount")
                if price is not None:
                    button.price = float(price)
                else:
                    print(f"Warning: Price not found in response for button ID {button.id}")
        except aiohttp.ClientError as e:
            print(f"Error fetching price for button ID {button.id}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for button ID {button.id}: {e}")

    async def fulfill_button_data(self, bs_product: BsProduct, buttons: List[Button]) -> BsProduct:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            tasks = [self._fetch_price_for_button(session, bs_product.id, int(button.id), button) for button in buttons]
            await asyncio.gather(*tasks)

        bs_product.list_button = buttons
        return bs_product

#
# if __name__ == "__main__":
#     # The ID for the digital catalog we want to query
#     section_id = 108056
#     ggservice = ggsell_service()
#     print(f"Fetching raw product data for catalog ID: {section_id}...")
#     raw_products = ggservice.get_category_data(section_id)
#
#     if raw_products:
#         print(f"Successfully fetched {len(raw_products)} products.")
#         print("\n--- Converting to BsProduct objects ---\n")
#
#         # Loop through the raw data and convert each item
#         bs_product_list = [ggservice.convert_to_BS_product(prod) for prod in raw_products]
#
#         # Print the details of the first few converted products
#         for i, product in enumerate(bs_product_list[:3]):
#             print(f"--- Product {i + 1} ---")
#             print(f"  Name: {product.name}")
#             print(f"  Seller: {product.seller_name}")
#             print(f"  Sold: {product.sold_count}")
#             # Use the get_price() method to see the calculated float price
#             print(f"  Price (USD): {product.get_price()}")
#             print(f"  Link: {product.link}")
#     else:
#         print("Failed to fetch product data.")
#

async def main():
    ggservice = ggsell_service()
    html_url = "https://ggsel.net/en/catalog/nintendo-eshop-giftcards-us"
    id_sec = ggservice.get_id_section_from_html(html_url)
    products = ggservice.get_category_data(id_sec)
    bsproduct = [ggservice.convert_to_BS_product(prod) for prod in products]
    first_product_data = bsproduct[0]
    prod_html = requests.get(first_product_data.link).text
    initial_buttons = ggservice.extract_buttons_from_html(prod_html)
    await ggservice.fulfill_button_data(first_product_data, initial_buttons)

    print("ok")

if __name__ == "__main__":
    asyncio.run(main())
