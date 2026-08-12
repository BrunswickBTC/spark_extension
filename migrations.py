from lnbits.db import Database


async def _ensure_tables(db: Database):
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS {db.schema}.deposit_addresses (
            id TEXT PRIMARY KEY, wallet_id TEXT NOT NULL, user_id TEXT NOT NULL,
            address TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'issued',
            txid TEXT, amount_sats {db.big_int},
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}, claimed_at TIMESTAMP
        )
    """)
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS {db.schema}.transfers (
            id TEXT PRIMARY KEY, wallet_id TEXT NOT NULL, user_id TEXT NOT NULL,
            direction TEXT NOT NULL, amount_sats {db.big_int}, receiver_address TEXT,
            provider_txid TEXT, status TEXT NOT NULL, provider_response TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        )
    """)


async def m001_initial(db: Database):
    await _ensure_tables(db)


async def m002_add_deposit_index(db: Database):
    # m001 may already be recorded as applied from an earlier broken version.
    # Ensure the tables here as well so this migration repairs that state.
    await _ensure_tables(db)
    await db.execute(f"CREATE INDEX IF NOT EXISTS {db.schema}_deposit_wallet ON {db.schema}.deposit_addresses(wallet_id)")
    await db.execute(f"CREATE INDEX IF NOT EXISTS {db.schema}_deposit_status ON {db.schema}.deposit_addresses(status)")
    await db.execute(f"CREATE INDEX IF NOT EXISTS {db.schema}_transfer_wallet ON {db.schema}.transfers(wallet_id)")
    await db.execute(f"CREATE INDEX IF NOT EXISTS {db.schema}_transfer_provider ON {db.schema}.transfers(provider_txid)")
