# logic/batcher.py
import logging
from typing import List

from clients.digiseller_client import DigisellerClient
from logic.processor import consolidate_price_updates
from models.digiseller_models import ProductPriceUpdate


class PriceUpdateBatcher:
    """
    A class to batch product price updates and send them in bulk.
    It acts as a context manager to ensure the final batch is always sent.
    """

    def __init__(self, client: DigisellerClient, batch_size: int = 20):
        """
        Initializes the batch processor.

        Args:
            client: The DigisellerClient instance to use for API calls.
            batch_size: The number of updates to collect before sending.
        """
        if batch_size < 1:
            raise ValueError("Batch size must be at least 1.")
        self.client = client
        self.batch_size = batch_size
        self._batch: List[ProductPriceUpdate] = []

    async def __aenter__(self):
        """Enter the async context, returning self."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context, flushing any remaining items."""
        logging.info("Exiting batcher context, flushing final batch...")
        await self.flush()

    async def add(self, item: ProductPriceUpdate):
        """
        Adds an item to the batch and flushes the batch if it's full.
        """
        self._batch.append(item)
        if len(self._batch) >= self.batch_size:
            await self.flush()

    async def flush(self):
        """
        Sends all items currently in the batch to the API.
        """
        if not self._batch:
            return

        logging.info(f"Flushing batch of {len(self._batch)} price updates...")
        try:
            self._batch = consolidate_price_updates(self._batch)
            response = await self.client.bulk_update_prices(self._batch)
            if response.taskId:
                logging.info(f"Batch update successful. Task ID: {response.taskId}")
            else:
                logging.error(f"Batch update failed: {response.return_description}")
        except Exception as e:
            logging.error(f"An error occurred during batch flush: {e}", exc_info=True)
        finally:
            self._batch.clear()
