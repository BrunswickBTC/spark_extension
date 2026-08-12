from __future__ import annotations

import hashlib
from typing import Any

from bolt11 import decode as bolt11_decode
from loguru import logger

from lnbits.core.crud import create_payment, get_wallet, get_standalone_payment
from lnbits.core.db import db as core_db
from lnbits.core.models import CreatePayment, PaymentState
from lnbits.wallets import fake_wallet

from .client import SparkSidecarClient
from .crud import (
    GLOBAL_WALLET_KEY,
    create_transfer,
    get_setting,
    list_reconcilable_deposits,
    mark_deposit_credited,
    reserve_deposit,
    get_transfer_by_provider,
)
from .events import publish

INTERVAL_SECONDS = 60
SPARK_TAG = "#spark-l2"
SPARK_RECEIVE_MEMO = "Spark tokens received via funding source"


def transaction_key(namespace: str, *parts: object) -> str:
    digest = hashlib.sha256(":".join([namespace, *(str(p) for p in parts)]).encode()).hexdigest()
    return f"sparkl2_{namespace}_{digest}"


def credit_key(deposit_id: str, txid: str, vout: int) -> str:
    return transaction_key("onchain", deposit_id, txid, vout)


def _nested_value(value: Any, *keys: str):
    if not isinstance(value, dict):
        return None
    for key in keys:
        if value.get(key) is not None:
            return value[key]
    return None


def _text_identity(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("value") or value.get("hex") or value.get("publicKey") or value.get("identityPublicKey")
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex()
    return str(value).lower() if value is not None else None


def _is_direct_incoming_spark_transfer(transfer: dict[str, Any], local_identity: str | None) -> bool:
    transfer_type = str(transfer.get("type") or "").upper()
    direction = str(transfer.get("transferDirection") or transfer.get("transfer_direction") or "").upper()
    request = transfer.get("userRequest") if isinstance(transfer.get("userRequest"), dict) else {}
    request_kind = str(request.get("type") or request.get("requestType") or "").upper()
    if transfer_type not in {"TRANSFER", "SPARK_TRANSFER"}:
        return False
    if direction not in {"INCOMING", "IN"}:
        return False
    if request_kind in {"LIGHTNING_RECEIVE", "LIGHTNING_SEND", "COOP_EXIT", "CLAIM_STATIC_DEPOSIT", "LEAVES_SWAP"}:
        return False
    receiver = _text_identity(transfer.get("receiverIdentityPublicKey") or transfer.get("receiver_identity_public_key") or request.get("receiverIdentityPublicKey") or request.get("receiver_identity_public_key"))
    return bool(receiver and local_identity and receiver == local_identity)

def parse_utxo(utxo: dict[str, Any]) -> tuple[str, int, int]:
    txid, vout, amount = utxo.get("txid"), utxo.get("vout"), utxo.get("amount_sats")
    if not isinstance(txid, str) or not txid:
        raise ValueError("UTXO is missing txid")
    if not isinstance(vout, int) or vout < 0:
        raise ValueError("UTXO is missing a valid vout")
    try:
        amount_sats = int(amount)
    except (TypeError, ValueError) as exc:
        raise ValueError("UTXO is missing amount_sats") from exc
    if amount_sats <= 0:
        raise ValueError("UTXO amount_sats must be positive")
    return txid, vout, amount_sats


async def record_internal_credit(wallet, amount_sats: int, checking_id: str, memo: str, source: str = SPARK_TAG) -> bool:
    response = await fake_wallet.create_invoice(abs(amount_sats), memo=memo)
    invoice = bolt11_decode(response.payment_request)
    payment = CreatePayment(
        wallet_id=wallet.source_wallet_id,
        bolt11=response.payment_request,
        payment_hash=invoice.payment_hash,
        preimage=response.preimage,
        amount_msat=amount_sats * 1000,
        memo=memo,
        extra={"tag": source},
    )
    try:
        await create_payment(checking_id=checking_id, data=payment, status=PaymentState.SUCCESS)
    except ValueError as exc:
        if "already exists" in str(exc).lower():
            return False
        raise
    return True


async def reconcile_onchain(client: SparkSidecarClient) -> None:
    for record in await list_reconcilable_deposits():
        try:
            if record["status"] == "issued":
                result = await client.request(
                    "deposit_utxos",
                    {"address": record["address"], "limit": 100, "offset": 0, "exclude_claimed": True},
                )
                for raw_utxo in result.get("utxos", []) if isinstance(result, dict) else []:
                    txid, vout, amount_sats = parse_utxo(raw_utxo)
                    if await reserve_deposit(record["id"], txid, vout):
                        record = {**record, "status": "claiming", "txid": txid, "vout": vout, "amount_sats": amount_sats}
                        break
                else:
                    continue
            txid, vout, amount_sats = record.get("txid"), record.get("vout"), record.get("amount_sats")
            if not isinstance(txid, str) or not isinstance(vout, int) or not amount_sats:
                continue
            try:
                await client.request("deposit_claim", {"txid": txid})
            except Exception as exc:
                if "already" not in str(exc).lower() and "used" not in str(exc).lower():
                    raise
            wallet = await get_wallet(record["wallet_id"])
            if not wallet:
                raise RuntimeError(f"Destination wallet {record['wallet_id']} not found")
            credited = await record_internal_credit(
                wallet,
                int(amount_sats),
                transaction_key("onchain", record["id"], txid, vout),
                f"Spark on-chain deposit {txid}:{vout}",
            )
            await mark_deposit_credited(record["id"], txid, vout, int(amount_sats))
            existing_payment = await core_db.fetchone("SELECT checking_id FROM apipayments WHERE memo = :memo AND wallet = :wallet_id ORDER BY time DESC LIMIT 1", {"memo": f"Spark on-chain deposit {txid}:{vout}", "wallet_id": wallet.source_wallet_id})
            if not await get_transfer_by_provider(txid):
                await create_transfer(record["wallet_id"], record["user_id"], int(amount_sats), record["address"], txid, "credited", {"txid": txid, "vout": vout, "ledger_checking_id": existing_payment["checking_id"] if existing_payment else None}, f"Spark on-chain deposit {txid}:{vout}", transaction_type="onchain", direction="credit", source="#spark-l2")
            publish({"type": "onchain_credited", "deposit_id": record["id"], "txid": txid, "vout": vout, "amount_sats": int(amount_sats), "credited": credited})
        except Exception as exc:
            logger.warning("Spark on-chain reconciliation failed for {}: {}", record.get("id"), exc)


async def reconcile_spark_transfers(client: SparkSidecarClient) -> None:
    wallet_id = await get_setting(GLOBAL_WALLET_KEY)
    if not wallet_id:
        return
    wallet = await get_wallet(wallet_id)
    if not wallet:
        logger.warning("Configured global Spark receive wallet {} no longer exists", wallet_id)
        return
    identity = await client.request("identity")
    receiver_identity = identity.get("identity_public_key") if isinstance(identity, dict) else None
    if not receiver_identity:
        return
    result = await client.request("transfers", {"limit": 100, "offset": 0})
    transfers = result.get("transfers", []) if isinstance(result, dict) else result if isinstance(result, list) else []
    logger.info("Spark receive reconciliation: selected_wallet={} provider_transfers={}", wallet_id, len(transfers))
    for transfer in transfers:
        if not isinstance(transfer, dict):
            continue
        status = str(transfer.get("status") or _nested_value(transfer.get("userRequest"), "status") or "").upper()
        if status not in {"COMPLETED", "TRANSFER_COMPLETED", "TRANSFER_STATUS_COMPLETED"}:
            logger.debug("Skipping Spark transfer {} with status {}", transfer.get("id") or transfer.get("transfer_id"), status)
            continue
        if not _is_direct_incoming_spark_transfer(transfer, _text_identity(receiver_identity)):
            logger.debug("Skipping non-direct incoming Spark transfer {} type={} direction={}", transfer.get("id") or transfer.get("transfer_id"), transfer.get("type"), transfer.get("transferDirection"))
            continue
        request = transfer.get("userRequest") if isinstance(transfer.get("userRequest"), dict) else {}
        amount = transfer.get("totalValue") or transfer.get("total_value") or transfer.get("amountSats") or request.get("amountSats") or request.get("amount_sats")
        txid = transfer.get("id") or transfer.get("transfer_id") or transfer.get("transaction_id")
        if not txid or not amount:
            logger.warning("Skipping Spark transfer with missing id/amount: {}", transfer)
            continue
        amount = int(amount)
        memo = SPARK_RECEIVE_MEMO
        if await get_transfer_by_provider(txid):
            logger.debug("Spark transfer {} already has a local audit record", txid)
            continue
        try:
            credited = await record_internal_credit(wallet, amount, transaction_key("spark_receive", txid), memo)
            receive_user = await core_db.fetchone("SELECT accounts.id AS user_id FROM wallets JOIN accounts ON accounts.id = wallets.user WHERE wallets.id = :wallet_id", {"wallet_id": wallet_id})
            await create_transfer(wallet_id, receive_user["user_id"] if receive_user else "unknown", amount, str(receiver_identity), txid, "credited", transfer, memo, transaction_type="spark", direction="credit", source="#spark-l2")
            logger.info("Credited incoming Spark transfer {}: {} sats to wallet {} (new_credit={})", txid, amount, wallet_id, credited)
            publish({"type": "spark_received", "transaction_id": txid, "amount_sats": amount, "wallet_id": wallet_id, "credited": credited})
        except Exception:
            logger.exception("Failed to credit incoming Spark transfer {} to wallet {}", txid, wallet_id)


async def reconcile_once() -> None:
    client = SparkSidecarClient()
    try:
        await reconcile_onchain(client)
        await reconcile_spark_transfers(client)
    except Exception as exc:
        logger.warning("Spark reconciliation cycle failed: {}", exc)
    finally:
        await client.close()


async def deposit_reconciliation_task() -> None:
    from lnbits.tasks import run_interval

    await run_interval(INTERVAL_SECONDS, reconcile_once)()
