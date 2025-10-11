import asyncio

from clients.digiseller_client import DigisellerClient
from services.digiseller_service import get_product_description


async def do_find_product_description(product_id: int) -> str:
    result = await get_product_description(client=DigisellerClient(), product_id=product_id)
    if result is None:
        return ""
    variants = result.get('variants', [])
    # base_price = result.get('base_price')
    if len(variants) == 0:
        # print(f"Base price: {base_price}")
        print("No variants")
    else:
        # print(f"Base price: {base_price}")
        for variant in variants:
            variant_id = variant.value
            variant_name = variant.text
            print(f"Variant ID: {variant_id}, Name: {variant_name}")


if __name__ == "__main__":
    while True:
        try:
            _product_id = int(input("\nEnter product ID: "))
            asyncio.run(do_find_product_description(_product_id))
        except ValueError:
            print("Invalid input. Please enter a valid product ID.")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
