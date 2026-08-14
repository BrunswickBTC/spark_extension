from __future__ import annotations

from typing import Any

import httpx
from lnbits.settings import settings


_ROUTES = {
    "capabilities": ("GET", "/v1/capabilities"),
    "balance": ("POST", "/v1/balance"),
    "identity": ("GET", "/v1/identity"),
    "settings": ("GET", "/v1/settings"),
    "optimization": ("POST", "/v1/status/optimization"),
    "single_use_deposit": ("GET", "/v1/deposit/single-use"),
    "static_deposit": ("GET", "/v1/deposit/static"),
    "static_addresses": ("GET", "/v1/deposit/static/addresses"),
    "deposit_utxos": ("POST", "/v1/deposit/utxos"),
    "deposit_claim": ("POST", "/v1/deposit/claim"),
    "transfers": ("POST", "/v1/transfers/list"),
    "transfer": ("POST", "/v1/transfer"),
    "transfer_get": ("POST", "/v1/transfer/get"),
    "transfer_ssp": ("POST", "/v1/transfer/ssp"),
    "token_transfer": ("POST", "/v1/tokens/transfer"),
    "token_transactions": ("POST", "/v1/tokens/transactions"),
    "withdrawal_quote": ("POST", "/v1/withdraw/quote"),
    "withdrawal": ("POST", "/v1/withdraw"),
    "withdrawal_get": ("POST", "/v1/withdraw/get"),
}


def sidecar_path(operation: str) -> tuple[str, str]:
    try:
        return _ROUTES[operation]
    except KeyError as exc:
        raise ValueError(f"Unsupported Spark sidecar route: {operation}") from exc


class SparkSidecarClient:
    def __init__(self) -> None:
        endpoint = settings.spark_l2_external_endpoint or "http://127.0.0.1:8765"
        self.client = httpx.AsyncClient(
            base_url=endpoint.rstrip("/"),
            headers={"X-Api-Key": settings.spark_l2_external_api_key or ""},
            timeout=60,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def request(self, operation: str, payload: dict[str, Any] | None = None) -> Any:
        method, path = sidecar_path(operation)
        response = await self.client.request(method, path, json=payload)
        if response.is_error:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise httpx.HTTPStatusError(
                f"Spark sidecar returned HTTP {response.status_code}: {detail}",
                request=response.request,
                response=response,
            )
        return response.json()
