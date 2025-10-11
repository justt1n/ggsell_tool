import asyncio

from services.digiseller_service import get_all_items, items_to_sheet

prods = asyncio.run(get_all_items())
asyncio.run(items_to_sheet(prods))
