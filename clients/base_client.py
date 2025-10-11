# file: clients/base_client.py

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, RetryCallState

import constants
from clients.exceptions import QueueLimitExceededError

logger = logging.getLogger(__name__)


async def _log_failed_request(e: httpx.RequestError):
    """Hàm trợ giúp để ghi lại thông tin chi tiết của một request thất bại."""
    request = e.request
    logger.error("--- FAILED REQUEST DETAILS ---")
    logger.error(f"Method: {request.method}")
    logger.error(f"URL: {request.url}")
    logger.error(f"Headers: {dict(request.headers)}")

    try:
        body = await request.aread()
        if body:
            try:
                parsed_body = json.loads(body)
                pretty_body = json.dumps(parsed_body, indent=2, ensure_ascii=False)
                logger.error(f"Body:\n{pretty_body}")
            except json.JSONDecodeError:
                logger.error(f"Body (raw): {body.decode(errors='ignore')}")
        else:
            logger.error("Body: (empty)")
    except Exception as read_exc:
        logger.error(f"Failed to read request body for logging: {read_exc}")

    if isinstance(e, httpx.HTTPStatusError):
        response = e.response
        logger.error("--- FAILED RESPONSE DETAILS ---")
        logger.error(f"Status Code: {response.status_code}")
        logger.error(f"Response Body: {response.text}")
    logger.error("------------------------------")


def _is_retryable_exception(retry_state: RetryCallState) -> bool:
    exception = retry_state.outcome.exception()

    if not exception:
        return False

    if isinstance(exception, QueueLimitExceededError):
        logger.warning(f"Queue limit exceeded. Retrying... Error: {exception}")
        return True

    if isinstance(exception, httpx.RequestError):
        if isinstance(exception, httpx.TimeoutException):
            return False
        logger.warning(f"Retryable network error occurred: {exception}. Retrying...")
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        status_code = exception.response.status_code
        if 500 <= status_code < 600:
            logger.warning(f"Retryable server error occurred (Status {status_code}). Retrying...")
            return True

    return False


class BaseAPIClient(ABC):
    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None):
        self._base_url = base_url
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers or constants.DEFAULT_HEADER,
            timeout=constants.DEFAULT_API_TIMEOUT,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self._client.aclose()

    @retry(
        wait=wait_exponential(multiplier=5, min=1, max=30),
        stop=stop_after_attempt(6),
        retry=_is_retryable_exception
    )
    async def _make_request(
            self,
            method: str,
            endpoint: str,
            params: Optional[Dict[str, Any]] = None,
            json_data: Optional[Any] = None
    ) -> httpx.Response:
        try:
            response = await self._client.request(method, endpoint, params=params, json=json_data)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400 and "The limit of tasks in the queue has been exceeded" in e.response.text:
                # logger.error(f"API task queue limit exceeded: {e.response.text}")
                raise QueueLimitExceededError(e.response.text) from e

            await _log_failed_request(e)
            raise

        except httpx.RequestError as e:
            await _log_failed_request(e)
            raise

    @abstractmethod
    async def _prepare_payload(self, auth_required: bool, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError

    async def get(self, endpoint: str, response_model: Type[BaseModel], auth_required: bool = False,
                  **kwargs: Any) -> Any:
        prepared_params = await self._prepare_payload(auth_required=auth_required, **kwargs)
        response = await self._make_request(method='GET', endpoint=endpoint, params=prepared_params)
        return response_model.model_validate(response.json())

    async def post(self, endpoint: str, response_model: Type[BaseModel], auth_required: bool = False,
                   **kwargs: Any) -> Any:
        json_payload = await self._prepare_payload(auth_required=auth_required, **kwargs)
        response = await self._make_request(method='POST', endpoint=endpoint, json_data=json_payload)
        return response_model.model_validate(response.json())
