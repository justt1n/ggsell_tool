import asyncio
import re
from typing import List, Optional, Dict
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from models.digiseller_models import InsideProduct
from models.sheet_models import Payload
from services.digiseller_service import get_all_items, items_to_sheet, get_product_description

from clients.digiseller_client import DigisellerClient


def extract_price_options_with_url(html_str: str, currency: str = 'USD') -> List[InsideProduct]:
    if not html_str:
        return []

    soup = BeautifulSoup(html_str, 'html.parser')
    options_data = []

    options_container = soup.find('div', class_='id_chips_container')
    if not options_container:
        return []

    price_chips = options_container.find_all('div', class_='chips--large')

    for chip in price_chips:
        input_tag = chip.find('input', class_='chips__input')
        label_tag = chip.find('label', class_='chips__label')

        if not (input_tag and label_tag):
            continue

        item_id = input_tag.get('data-item-id')
        option_id = input_tag.get('data-id')
        value_id = input_tag.get('value')

        price_text = label_tag.get_text(strip=True)

        currency_match = re.search(r'[A-Za-z]+', price_text)
        if currency_match:
            currency = currency_match.group(0).upper()

        if all([item_id, option_id, value_id, currency]):
            xml_payload = f'<response><option O="{option_id}" V="{value_id}"/></response>'
            encoded_xml = quote_plus(xml_payload)

            request_url = (
                "https://plati.market/asp/price_options.asp?"
                f"p={item_id}&"
                f"c={currency}&"
                f"x={encoded_xml}"
            )

            item = InsideProduct(
                price_text=price_text,
                request_url=request_url
            )

            options_data.append(item)
    return options_data


# response = requests.get("https://plati.market/itm/auto-steam-turkey-global-gift-key-code-usa-usd/3668317")
# response.raise_for_status()
# full_html_str = response.text
#
# # Chạy hàm để lấy list URL
# list_of_urls = extract_price_options_with_url(full_html_str)
#
# # In ra kết quả
# print(f"Đã tìm thấy {len(list_of_urls)} URL request:\n")
# for url in list_of_urls:
#     print(f"Text: {url.price_text:<10} | URL: {url.request_url}")
#     response = requests.get(url.request_url)
#     response.raise_for_status()
#     print(f"URL: {url}\nResponse: {response.text}\n")
#     print("-" * 80)

async def main():
    a = await get_product_description(client=DigisellerClient())
    print(a)

if __name__ == "__main__":
    asyncio.run(main())
