from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from lnbits.decorators import check_admin, check_user_exists
from loguru import logger

from .client import SparkSidecarClient
from .events import events_response
from .events import publish as publish_event
from .reconciler import record_internal_credit, transaction_key
from .crud import (create_deposit, get_active_deposit, get_deposit, get_deposit_by_address, list_deposits, mark_deposit_claimed, create_transfer, get_transfer_by_provider, get_setting, set_setting, GLOBAL_WALLET_KEY)
from lnbits.core.crud import get_wallet, get_user, get_accounts
from lnbits.core.db import db as core_db
from lnbits.db import Filters
from . import db
from .models import (
    DepositUtxosRequest,
    IdentifierRequest,
    SparkTransferRequest,
    TokenTransactionsRequest,
    TokenTransferRequest,
    TransfersRequest,
    WithdrawalQuoteRequest,
    WithdrawalRequest,
    ReceiveAddressRequest,
    DepositClaimRequest,
    GlobalWalletRequest,
)

sparkl2_api_router = APIRouter()


@sparkl2_api_router.get("/api/v1/events", dependencies=[Depends(check_user_exists)])
async def api_events(request: Request):
    return await events_response(request)
_transfers_cache: Any = None
_transfers_cache_at = 0.0
_transfers_lock = asyncio.Lock()


def _model_data(model: Any, *, exclude_none: bool = False) -> dict[str, Any]:
    dump = getattr(model, "model_dump", None)
    if callable(dump):
        return dump(exclude_none=exclude_none)
    return model.dict(exclude_none=exclude_none)


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


@sparkl2_api_router.post("/api/v1/balance", dependencies=[Depends(check_user_exists)])
async def api_balance():
    return await _call("balance")


@sparkl2_api_router.get("/api/v1/identity", dependencies=[Depends(check_user_exists)])
async def api_identity():
    return await _call("identity")


@sparkl2_api_router.get("/api/v1/deposit/single-use", dependencies=[Depends(check_user_exists)])
async def api_single_use_deposit():
    return await _call("single_use_deposit")


@sparkl2_api_router.get("/api/v1/deposit/static", dependencies=[Depends(check_user_exists)])
async def api_static_deposit():
    return await _call("static_deposit")


@sparkl2_api_router.post("/api/v1/transfers", dependencies=[Depends(check_user_exists)])
async def api_transfers(data: TransfersRequest, user=Depends(check_admin)):
    global _transfers_cache, _transfers_cache_at
    async with _transfers_lock:
        result = await _call("transfers", _model_data(data, exclude_none=True))
        provider_rows = result if isinstance(result, list) else result.get("transfers", result.get("data", result.get("items", []))) if isinstance(result, dict) else []
        wallet_rows = await core_db.fetchall("SELECT wallets.id AS wallet_id, wallets.name AS wallet_name, accounts.id AS user_id, COALESCE(accounts.username, accounts.email, accounts.id) AS user_name FROM wallets JOIN accounts ON accounts.id = wallets.user WHERE wallets.deleted = false")
        wallet_map = {str(row["wallet_id"]): row for row in wallet_rows}
        local_rows = await db.fetchall("SELECT id, wallet_id, direction, transaction_type, source, amount_sats, provider_txid, status, provider_response, created_at FROM sparkl2.transfers ORDER BY created_at DESC LIMIT 100")
        local_map = {str(row["provider_txid"]): row for row in local_rows if row.get("provider_txid")}
        enriched = []
        seen_provider_ids = set()
        for row in provider_rows:
            item = dict(row) if isinstance(row, dict) else {"provider": row}
            provider_ids = {str(value) for value in (item.get("id"), item.get("transfer_id"), item.get("transaction_id"), item.get("userRequestId"), item.get("user_request_id"), item.get("coopExitTxid"), item.get("coop_exit_txid")) if value}
            request = item.get("userRequest") if isinstance(item.get("userRequest"), dict) else {}
            provider_ids.update(str(value) for value in (request.get("id"), request.get("userRequestId"), request.get("user_request_id"), request.get("coopExitTxid"), request.get("coop_exit_txid")) if value)
            raw_provider = item.get("provider") if isinstance(item.get("provider"), dict) else {}
            provider_ids.update(str(value) for value in (raw_provider.get("id"), raw_provider.get("userRequestId"), raw_provider.get("coopExitTxid"), raw_provider.get("coop_exit_txid")) if value)
            nested_transfer = raw_provider.get("transfer") if isinstance(raw_provider.get("transfer"), dict) else {}
            provider_ids.update(str(value) for value in (nested_transfer.get("sparkId"), nested_transfer.get("userRequestId"), nested_transfer.get("id")) if value)
            local = next((local_map.get(value) for value in provider_ids if local_map.get(value)), None)
            provider_id = next(iter(provider_ids), None)
            if local:
                seen_provider_ids.add(str(local["provider_txid"]))
                item.update({"id": local["id"], "provider_txid": local["provider_txid"], "direction": local["direction"], "transaction_type": local["transaction_type"], "source": local["source"] or "#spark-l2", "wallet_id": local["wallet_id"], "wallet_name": wallet_map.get(str(local["wallet_id"]), {}).get("wallet_name"), "wallet_user": wallet_map.get(str(local["wallet_id"]), {}).get("user_name"), "amount_sats": local["amount_sats"], "ledger_status": local["status"], "created": local["created_at"].isoformat() if hasattr(local["created_at"], "isoformat") else str(local["created_at"])})
            else:
                item.update({"direction": item.get("direction") or "unknown", "transaction_type": item.get("transaction_type") or "spark", "source": item.get("source") or "#spark-l2", "wallet_id": None, "wallet_name": None, "wallet_user": None})
            enriched.append(item)
        for local in local_rows:
            if not local.get("provider_txid") or str(local["provider_txid"]) in seen_provider_ids:
                continue
            wallet = wallet_map.get(str(local["wallet_id"]), {})
            enriched.append({"id": local["id"], "direction": local["direction"], "transaction_type": local["transaction_type"], "source": local["source"] or "#spark-l2", "wallet_id": local["wallet_id"], "wallet_name": wallet.get("wallet_name"), "wallet_user": wallet.get("user_name"), "amount_sats": local["amount_sats"], "ledger_status": local["status"], "provider_txid": local["provider_txid"], "created": local["created_at"].isoformat() if hasattr(local["created_at"], "isoformat") else str(local["created_at"])})
        enriched.sort(key=lambda row: str(row.get("created") or row.get("createdAt") or row.get("userRequest", {}).get("createdAt") or ""), reverse=True)
        _transfers_cache = enriched
        _transfers_cache_at = time.monotonic()
        return enriched


@sparkl2_api_router.post("/api/v1/transfer", dependencies=[Depends(check_user_exists)])
async def api_transfer(data: SparkTransferRequest, user=Depends(check_user_exists)):
    wallet = next((w for w in user.wallets if w.id == data.wallet_id), None)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    fresh_wallet = await get_wallet(wallet.id)
    if not fresh_wallet:
        raise HTTPException(status_code=404, detail="Wallet not found after refresh")
    available_sats = int(fresh_wallet.balance_msat // 1000)
    if data.amount_sats > available_sats:
        raise HTTPException(status_code=400, detail=f"Insufficient wallet balance: {available_sats} sats available, {data.amount_sats} sats requested")
    result = await _call("transfer", {"amount_sats": data.amount_sats, "receiver_spark_address": data.receiver_spark_address, "memo": data.memo})
    provider_txid = result.get("id") or result.get("transfer_id") or result.get("transaction_id")
    # The shared sidecar balance is separate from LNbits accounting. Once the
    # provider accepts the transfer, debit the selected LNbits wallet so its
    # ledger reflects the outgoing Spark sats.
    try:
        await record_internal_credit(
            fresh_wallet,
            -data.amount_sats,
            transaction_key("spark_send", provider_txid or data.receiver_spark_address, data.amount_sats),
            data.memo or "Spark sats sent via funding source",
        )
    except Exception as exc:
        logger.error("Spark transfer {} succeeded but LNbits debit failed for wallet {}: {}", provider_txid, wallet.id, exc)
        await create_transfer(wallet.id, user.id, data.amount_sats, data.receiver_spark_address, provider_txid, "provider_succeeded_debit_failed", result, data.memo, transaction_type="spark", direction="debit", source="#spark-l2")
        raise HTTPException(status_code=502, detail="Spark transfer succeeded, but LNbits wallet debit failed; administrator reconciliation is required") from exc
    await create_transfer(wallet.id, user.id, data.amount_sats, data.receiver_spark_address, provider_txid, "submitted", result, data.memo, transaction_type="spark", direction="debit", source="#spark-l2")
    return {"transaction_id": provider_txid, "provider": result, "wallet_id": wallet.id, "debited_sats": data.amount_sats}


@sparkl2_api_router.post("/api/v1/receive/onchain", dependencies=[Depends(check_user_exists)])
async def api_receive_onchain(data: ReceiveAddressRequest, user=Depends(check_user_exists)):
    wallet = next((w for w in user.wallets if w.id == data.wallet_id), None)
    if not wallet:
        raise HTTPException(status_code=403, detail="Wallet does not belong to this user")
    existing = await get_active_deposit(wallet.id)
    if existing:
        return {"deposit_id": existing["id"], "wallet_id": wallet.id, "address": existing["address"], "status": existing["status"], "existing": True}
    result = await _call("single_use_deposit")
    address = result.get("address")
    if not address:
        raise HTTPException(status_code=502, detail="Sidecar returned no deposit address")
    record = await create_deposit(wallet.id, user.id, address)
    return {"deposit_id": record["id"], "wallet_id": wallet.id, "address": address, "status": "issued"}


@sparkl2_api_router.get("/api/v1/receive/onchain", dependencies=[Depends(check_user_exists)])
async def api_receive_onchain_list(user=Depends(check_user_exists)):
    return await list_deposits(user.id)


@sparkl2_api_router.get("/api/v1/admin/global-wallets", dependencies=[Depends(check_admin)])
async def api_admin_global_wallets():
    return await core_db.fetchall("""
        SELECT wallets.id AS wallet_id, wallets.name AS wallet_name,
               accounts.id AS user_id, COALESCE(accounts.username, accounts.email, accounts.id) AS user_name
        FROM wallets JOIN accounts ON accounts.id = wallets.user
        WHERE wallets.deleted = false AND wallets.shared_wallet_id IS NULL AND accounts.activated = true
        ORDER BY user_name, wallet_name
    """)


@sparkl2_api_router.get("/api/v1/admin/global-wallet", dependencies=[Depends(check_admin)])
async def api_admin_global_wallet():
    return {"wallet_id": await get_setting(GLOBAL_WALLET_KEY)}


@sparkl2_api_router.put("/api/v1/admin/global-wallet", dependencies=[Depends(check_admin)])
async def api_admin_set_global_wallet(data: GlobalWalletRequest):
    row = await core_db.fetchone("SELECT wallets.id FROM wallets JOIN accounts ON accounts.id = wallets.user WHERE wallets.id = :id AND wallets.deleted = false AND wallets.shared_wallet_id IS NULL AND accounts.activated = true", {"id": data.wallet_id})
    if not row:
        raise HTTPException(status_code=404, detail="Wallet not found")
    await set_setting(GLOBAL_WALLET_KEY, data.wallet_id)
    return {"wallet_id": data.wallet_id}


@sparkl2_api_router.get("/api/v1/admin/deposits", dependencies=[Depends(check_admin)])
async def api_admin_deposits():
    return await list_deposits()


@sparkl2_api_router.post("/api/v1/admin/deposit/claim", dependencies=[Depends(check_admin)])
async def api_admin_deposit_claim(data: DepositClaimRequest):
    record = await get_deposit(data.deposit_id)
    if not record:
        raise HTTPException(status_code=404, detail="Deposit address not found")
    if record["status"] == "credited":
        return {"status": "credited", "deposit_id": data.deposit_id}
    await _call("deposit_claim", {"txid": data.txid})
    wallet = await get_wallet(record["wallet_id"])
    if not wallet:
        raise HTTPException(status_code=404, detail="Destination wallet not found")
    await record_internal_credit(
        wallet,
        data.amount_sats,
        transaction_key("onchain", data.deposit_id, data.txid, 0),
        "Spark on-chain deposit",
    )
    await mark_deposit_claimed(data.deposit_id, data.txid, data.amount_sats)
    return {"status": "credited", "deposit_id": data.deposit_id, "wallet_id": record["wallet_id"], "txid": data.txid}


@sparkl2_api_router.post("/api/v1/withdrawal/user", dependencies=[Depends(check_user_exists)])
async def api_user_withdrawal(data: WithdrawalRequest, user=Depends(check_user_exists)):
    wallet = next((w for w in user.wallets if w.id == data.wallet_id), None)
    if not wallet:
        raise HTTPException(status_code=403, detail="Wallet does not belong to this user")
    fresh_wallet = await get_wallet(wallet.id)
    if not fresh_wallet:
        raise HTTPException(status_code=404, detail="Wallet not found after refresh")
    if data.amount_sats:
        available_sats = int(fresh_wallet.balance_msat // 1000)
        wallet_debit = data.amount_sats + (data.fee_amount_sats if not data.deduct_fee_from_withdrawal_amount else 0)
        if wallet_debit > available_sats:
            raise HTTPException(status_code=400, detail=f"Insufficient wallet balance: {available_sats} sats available, {wallet_debit} sats required including the withdrawal fee")
    result = await _call("withdrawal", _model_data(data, exclude_none=True))
    provider_id = result.get("id") or result.get("transaction_id") or result.get("request_id")
    provider_transfer = result.get("transfer") if isinstance(result, dict) else None
    if isinstance(provider_transfer, dict):
        transfer_id = provider_transfer.get("id") or provider_transfer.get("sparkId") or provider_transfer.get("userRequestId")
        provider_id = provider_id or transfer_id
    provider_txid = (result.get("coopExitTxid") or result.get("coop_exit_txid") or result.get("transaction_id") or provider_id) if isinstance(result, dict) else provider_id
    fee_sats = int(data.fee_amount_sats)
    wallet_debit = data.amount_sats + (0 if data.deduct_fee_from_withdrawal_amount else fee_sats)
    if data.amount_sats:
        await record_internal_credit(
            wallet,
            -wallet_debit,
            transaction_key("onchain_send", provider_id or data.onchain_address, data.amount_sats, fee_sats),
            data.memo or f"Bitcoin on-chain payment via funding source (fee {fee_sats} sats)",
        )
    await create_transfer(wallet.id, user.id, wallet_debit, data.onchain_address, provider_txid, result.get("status", "submitted") if isinstance(result, dict) else "submitted", result, data.memo, transaction_type="onchain", direction="debit", source="#spark-l2")
    return {"status": "submitted", "wallet_id": wallet.id, "provider": result}


@sparkl2_api_router.post("/api/v1/tokens/transfer", dependencies=[Depends(check_admin)])
async def api_token_transfer(data: TokenTransferRequest):
    return await _call("token_transfer", _model_data(data, exclude_none=True))


@sparkl2_api_router.post("/api/v1/withdrawal/quote/user", dependencies=[Depends(check_user_exists)])
async def api_user_withdrawal_quote(data: WithdrawalQuoteRequest, user=Depends(check_user_exists)):
    wallet = next((w for w in user.wallets if w.id == getattr(data, "wallet_id", None)), None)
    if not wallet:
        raise HTTPException(status_code=403, detail="Wallet does not belong to this user")
    quote = await _call("withdrawal_quote", _model_data(data, exclude_none=True))
    speed = (getattr(data, "exit_speed", "FAST") or "FAST").lower()
    suffix = {"fast": "Fast", "medium": "Medium", "slow": "Slow"}.get(speed, "Fast")
    def original_value(value):
        if isinstance(value, dict):
            return value.get("originalValue") or value.get("original_value") or value.get("value") or 0
        return getattr(value, "originalValue", None) or getattr(value, "original_value", None) or getattr(value, "value", 0) or 0
    user_fee = original_value(quote.get(f"userFee{suffix}") if isinstance(quote, dict) else getattr(quote, f"userFee{suffix}", None))
    l1_fee = original_value(quote.get(f"l1BroadcastFee{suffix}") if isinstance(quote, dict) else getattr(quote, f"l1BroadcastFee{suffix}", None))
    quote_id = quote.get("id") if isinstance(quote, dict) else getattr(quote, "id", None)
    normalized = dict(quote) if isinstance(quote, dict) else {"provider_quote": quote}
    normalized.update({"fee_quote_id": quote_id, "fee_amount_sats": int(user_fee) + int(l1_fee), "user_fee_sats": int(user_fee), "l1_broadcast_fee_sats": int(l1_fee), "exit_speed": data.exit_speed})
    return normalized


@sparkl2_api_router.post("/api/v1/withdrawal/quote", dependencies=[Depends(check_admin)])
async def api_withdrawal_quote(data: WithdrawalQuoteRequest):
    return await _call("withdrawal_quote", _model_data(data))


@sparkl2_api_router.post("/api/v1/withdrawal", dependencies=[Depends(check_admin)])
async def api_withdrawal(data: WithdrawalRequest):
    return await _call("withdrawal", _model_data(data))


@sparkl2_api_router.get("/api/v1/admin/status", dependencies=[Depends(check_admin)])
async def api_admin_status():
    results = {}
    for key, operation in (("settings", "settings"), ("optimization", "optimization"), ("static_addresses", "static_addresses")):
        try:
            results[key] = await _call(operation)
        except HTTPException as exc:
            results[key] = {"error": exc.detail}
    return results


@sparkl2_api_router.post("/api/v1/deposit/utxos", dependencies=[Depends(check_admin)])
async def api_deposit_utxos(data: DepositUtxosRequest):
    return await _call("deposit_utxos", _model_data(data, exclude_none=True))


@sparkl2_api_router.post("/api/v1/transfer/get", dependencies=[Depends(check_admin)])
async def api_transfer_get(data: IdentifierRequest):
    return await _call("transfer_get", _model_data(data))


@sparkl2_api_router.post("/api/v1/transfer/ssp", dependencies=[Depends(check_admin)])
async def api_transfer_ssp(data: IdentifierRequest):
    return await _call("transfer_ssp", _model_data(data))


@sparkl2_api_router.post("/api/v1/withdrawal/get", dependencies=[Depends(check_admin)])
async def api_withdrawal_get(data: IdentifierRequest):
    return await _call("withdrawal_get", _model_data(data))


@sparkl2_api_router.post("/api/v1/tokens/transactions", dependencies=[Depends(check_user_exists)])
async def api_token_transactions(data: TokenTransactionsRequest):
    return await _call("token_transactions", _model_data(data, exclude_none=True))
