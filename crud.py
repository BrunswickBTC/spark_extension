from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import uuid4
from . import db

async def create_deposit(wallet_id: str, user_id: str, address: str):
    row = {"id": uuid4().hex, "wallet_id": wallet_id, "user_id": user_id, "address": address, "status": "issued", "created_at": datetime.now(timezone.utc)}
    await db.execute("INSERT INTO sparkl2.deposit_addresses (id, wallet_id, user_id, address, status, created_at) VALUES (:id, :wallet_id, :user_id, :address, :status, :created_at)", row)
    return row

async def get_deposit(deposit_id: str):
    return await db.fetchone("SELECT * FROM sparkl2.deposit_addresses WHERE id = :id", {"id": deposit_id})

async def list_deposits(user_id: str | None = None):
    if user_id:
        return await db.fetchall("SELECT * FROM sparkl2.deposit_addresses WHERE user_id = :user ORDER BY created_at DESC", {"user": user_id})
    return await db.fetchall("SELECT * FROM sparkl2.deposit_addresses ORDER BY created_at DESC")

async def get_deposit_by_address(address: str):
    return await db.fetchone("SELECT * FROM sparkl2.deposit_addresses WHERE address = :address", {"address": address})

async def mark_deposit_claimed(deposit_id: str, txid: str, amount_sats: int):
    await db.execute("UPDATE sparkl2.deposit_addresses SET status = 'credited', txid = :txid, amount_sats = :amount, claimed_at = CURRENT_TIMESTAMP WHERE id = :id AND status != 'credited'", {"id": deposit_id, "txid": txid, "amount": amount_sats})

async def create_transfer(wallet_id: str, user_id: str, amount_sats: int, receiver: str, provider_txid: str | None, status: str, response):
    row = {"id": uuid4().hex, "wallet_id": wallet_id, "user_id": user_id, "direction": "out", "amount_sats": amount_sats, "receiver_address": receiver, "provider_txid": provider_txid, "status": status, "provider_response": json.dumps(response, default=str), "created_at": datetime.now(timezone.utc)}
    await db.execute("INSERT INTO sparkl2.transfers (id, wallet_id, user_id, direction, amount_sats, receiver_address, provider_txid, status, provider_response, created_at) VALUES (:id, :wallet_id, :user_id, :direction, :amount_sats, :receiver_address, :provider_txid, :status, :provider_response, :created_at)", row)
    return row
