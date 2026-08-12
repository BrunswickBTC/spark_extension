from __future__ import annotations

import hashlib
from typing import Any

from bolt11 import decode as bolt11_decode
from loguru import logger

from lnbits.core.crud import create_payment, get_wallet
from lnbits.core.models import CreatePayment, PaymentState
from lnbits.wallets import fake_wallet

from .client import SparkSidecarClient
from .crud import list_reconcilable_deposits, mark_deposit_credited, reserve_deposit

INTERVAL_SECONDS = 60


def credit_key(deposit_id: str, txid: str, vout: int) -> str:
    digest = hashlib.sha256(f"{deposit_id}:{txid}:{vout}".encode()).hexdigest()
    return f"sparkl2_deposit_{digest}"


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


async def credit_internal_deposit(record: dict[str, Any], txid: str, vout: int, amount_sats: int) -> None:
    wallet = await get_wallet(record["wallet_id"])
    if not wallet:
        raise RuntimeError(f"Destination wallet {record['wallet_id']} not found")
    response = await fake_wallet.create_invoice(amount_sats, memo=f"Spark on-chain deposit {txid}:{vout}")
    invoice = bolt11_decode(response.payment_request)
    try:
        await create_payment(
            checking_id=credit_key(record["id"], txid, vout),
            data=CreatePayment(
                wallet_id=wallet.source_wallet_id,
                bolt11=response.payment_request,
                payment_hash=invoice.payment_hash,
                preimage=response.preimage,
                amount_msat=amount_sats * 1000,
                memo=f"Spark on-chain deposit {txid}:{vout}",
            ),
            status=PaymentState.SUCCESS,
        )
    except ValueError as exc:
        if "already exists" not in str(exc).lower():
            raise
    await mark_deposit_credited(record["id"], txid, vout, amount_sats)


async def reconcile_once() -> None:
    deposits = await list_reconcilable_deposits()
    if not deposits:
        return
    client = SparkSidecarClient()
    try:
        for record in deposits:
            try:
                if record["status"] == "issued":
                    result = await client.request(
                        "deposit_utxos",
                        {"address": record["address"], "limit": 100, "offset": 0, "exclude_claimed": True},
                    )
                    utxos = result.get("utxos", []) if isinstance(result, dict) else []
                    for raw_utxo in utxos:
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
                await credit_internal_deposit(record, txid, vout, int(amount_sats))
            except Exception as exc:
                logger.warning("Spark deposit reconciliation failed for {}: {}", record.get("id"), exc)
    finally:
        await client.close()


async def deposit_reconciliation_task() -> None:
    from lnbits.tasks import run_interval

    await run_interval(INTERVAL_SECONDS, reconcile_once)()
