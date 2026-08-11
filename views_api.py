from __future__ import annotations

from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from lnbits.decorators import check_admin
from loguru import logger

from .client import SparkSidecarClient
from .models import DepositUtxosRequest, IdentifierRequest, TokenTransactionsRequest, TransfersRequest

sparkl2_api_router = APIRouter()


async def _call(operation: str, payload: dict[str, Any] | None = None) -> Any:
    client = SparkSidecarClient()
    try:
        return await client.request(operation, payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Spark L2 sidecar operation {} failed: {}", operation, exc)
        raise HTTPException(status_code=502, detail=f"Spark sidecar operation failed: {operation}") from exc
    finally:
        await client.close()


@sparkl2_api_router.get("/api/v1/balance", dependencies=[Depends(check_admin)])
async def api_balance():
    return await _call("balance")


@sparkl2_api_router.get("/api/v1/identity", dependencies=[Depends(check_admin)])
async def api_identity():
    return await _call("identity")


@sparkl2_api_router.get("/api/v1/settings", dependencies=[Depends(check_admin)])
async def api_settings():
    return await _call("settings")


@sparkl2_api_router.get("/api/v1/optimization", dependencies=[Depends(check_admin)])
async def api_optimization():
    return await _call("optimization")


@sparkl2_api_router.get("/api/v1/deposit/single-use", dependencies=[Depends(check_admin)])
async def api_single_use_deposit():
    return await _call("single_use_deposit")


@sparkl2_api_router.get("/api/v1/deposit/static", dependencies=[Depends(check_admin)])
async def api_static_deposit():
    return await _call("static_deposit")


@sparkl2_api_router.get("/api/v1/deposit/static/addresses", dependencies=[Depends(check_admin)])
async def api_static_addresses():
    return await _call("static_addresses")


@sparkl2_api_router.post("/api/v1/deposit/utxos", dependencies=[Depends(check_admin)])
async def api_deposit_utxos(data: DepositUtxosRequest):
    return await _call("deposit_utxos", data.model_dump(exclude_none=True))


@sparkl2_api_router.post("/api/v1/transfers", dependencies=[Depends(check_admin)])
async def api_transfers(data: TransfersRequest):
    return await _call("transfers", data.model_dump(exclude_none=True))


@sparkl2_api_router.post("/api/v1/transfer", dependencies=[Depends(check_admin)])
async def api_transfer(data: IdentifierRequest):
    return await _call("transfer", data.model_dump())


@sparkl2_api_router.post("/api/v1/transfer/ssp", dependencies=[Depends(check_admin)])
async def api_transfer_ssp(data: IdentifierRequest):
    return await _call("transfer_ssp", data.model_dump())


@sparkl2_api_router.post("/api/v1/withdrawal", dependencies=[Depends(check_admin)])
async def api_withdrawal(data: IdentifierRequest):
    return await _call("withdrawal", data.model_dump())


@sparkl2_api_router.post("/api/v1/tokens/transactions", dependencies=[Depends(check_admin)])
async def api_token_transactions(data: TokenTransactionsRequest):
    return await _call("token_transactions", data.model_dump(exclude_none=True))
