from __future__ import annotations

import json
from uuid import uuid4

from . import db


GLOBAL_WALLET_KEY = "receive_spark_wallet_id"


async def get_setting(key: str):
    row = await db.fetchone("SELECT value FROM sparkl2.settings WHERE key = :key", {"key": key})
    return row["value"] if row else None


async def set_setting(key: str, value: str):
    await db.execute(
        "INSERT INTO sparkl2.settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO UPDATE SET value = :value",
        {"key": key, "value": value},
    )


async def create_deposit(wallet_id: str, user_id: str, address: str):
    row = {"id": uuid4().hex, "wallet_id": wallet_id, "user_id": user_id, "address": address, "status": "issued"}
    await db.execute("INSERT INTO sparkl2.deposit_addresses (id, wallet_id, user_id, address, status) VALUES (:id, :wallet_id, :user_id, :address, :status)", row)
    return await db.fetchone("SELECT * FROM sparkl2.deposit_addresses WHERE id = :id", {"id": row["id"]})


async def get_deposit(deposit_id: str):
    return await db.fetchone("SELECT * FROM sparkl2.deposit_addresses WHERE id = :id", {"id": deposit_id})


async def list_deposits(user_id: str | None = None):
    if user_id:
        return await db.fetchall("SELECT * FROM sparkl2.deposit_addresses WHERE user_id = :user ORDER BY created_at DESC", {"user": user_id})
    return await db.fetchall("SELECT * FROM sparkl2.deposit_addresses ORDER BY created_at DESC")


async def list_reconcilable_deposits():
    return await db.fetchall("SELECT * FROM sparkl2.deposit_addresses WHERE status IN ('issued', 'claiming') ORDER BY created_at ASC")


async def get_active_deposit(wallet_id: str):
    return await db.fetchone("SELECT * FROM sparkl2.deposit_addresses WHERE wallet_id = :wallet_id AND status != 'credited' ORDER BY created_at DESC LIMIT 1", {"wallet_id": wallet_id})


async def get_deposit_by_address(address: str):
    return await db.fetchone("SELECT * FROM sparkl2.deposit_addresses WHERE address = :address", {"address": address})


async def reserve_deposit(deposit_id: str, txid: str, vout: int) -> bool:
    result = await db.execute("UPDATE sparkl2.deposit_addresses SET status = 'claiming', txid = :txid, vout = :vout WHERE id = :id AND status = 'issued'", {"id": deposit_id, "txid": txid, "vout": vout})
    return result.rowcount == 1


async def mark_deposit_credited(deposit_id: str, txid: str, vout: int, amount_sats: int):
    await db.execute("UPDATE sparkl2.deposit_addresses SET status = 'credited', txid = :txid, vout = :vout, amount_sats = :amount, claimed_at = CURRENT_TIMESTAMP WHERE id = :id AND status = 'claiming' AND txid = :txid AND vout = :vout", {"id": deposit_id, "txid": txid, "vout": vout, "amount": amount_sats})


async def mark_deposit_claimed(deposit_id: str, txid: str, amount_sats: int):
    await db.execute("UPDATE sparkl2.deposit_addresses SET status = 'credited', txid = :txid, amount_sats = :amount, claimed_at = CURRENT_TIMESTAMP WHERE id = :id AND status != 'credited'", {"id": deposit_id, "txid": txid, "amount": amount_sats})


async def get_transfer_by_provider(provider_txid: str):
    return await db.fetchone("SELECT * FROM sparkl2.transfers WHERE provider_txid = :provider_txid LIMIT 1", {"provider_txid": provider_txid})


async def create_transfer(wallet_id: str, user_id: str, amount_sats: int, receiver: str, provider_txid: str | None, status: str, response, memo: str = "", transaction_type: str = "spark", direction: str = "debit", source: str = "#spark-l2"):
    row = {"id": uuid4().hex, "wallet_id": wallet_id, "user_id": user_id, "direction": direction, "transaction_type": transaction_type, "source": source, "amount_sats": amount_sats, "receiver_address": receiver, "provider_txid": provider_txid, "status": status, "provider_response": json.dumps({"memo": memo, "provider": response}, default=str)}
    await db.execute("INSERT INTO sparkl2.transfers (id, wallet_id, user_id, direction, transaction_type, source, amount_sats, receiver_address, provider_txid, status, provider_response) VALUES (:id, :wallet_id, :user_id, :direction, :transaction_type, :source, :amount_sats, :receiver_address, :provider_txid, :status, :provider_response)", row)
    return await db.fetchone("SELECT * FROM sparkl2.transfers WHERE id = :id", {"id": row["id"]})
