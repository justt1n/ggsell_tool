import json
from typing import Optional

import requests
from bs4 import BeautifulSoup


def extract_json_from_html_by_type(soup: BeautifulSoup) -> list:
    """
    Finds and extracts all JSON objects embedded within an HTML document.

    This function specifically looks for JSON inside <script> tags,
    prioritizing those with `type="application/ld+json"`, as this is a
    standard way to embed structured data (like Schema.org data) in web pages.

    Args:
        soup: A BeautifulSoup object representing the parsed HTML content.

    Returns:
        A list of Python dictionaries or lists, where each item is a
        valid JSON object found on the page. Returns an empty list if no
        valid JSON is found.
    """
    json_objects = []

    script_tags = soup.find_all('script', type='application/json')

    for tag in script_tags:
        if tag.string:
            try:
                json_data = json.loads(tag.string)
                json_objects.append(json_data)
            except json.JSONDecodeError:
                continue

    return json_objects


def extract_json_from_html(soup: BeautifulSoup) -> Optional[dict]:
    """Extracts the __NEXT_DATA__ JSON blob from the HTML."""
    script_tag = soup.find('script', id='__NEXT_DATA__')
    if script_tag:
        try:
            return json.loads(script_tag.string)
        except json.JSONDecodeError:
            print("Could not decode __NEXT_DATA__ JSON.")
            return None
    return None


# This block demonstrates how to use the function.
if __name__ == '__main__':
    url = "https://ggsel.net/en/catalog/nintendo-eshop-giftcards-us"
