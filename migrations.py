async def m001_initial(db):
    await db.execute("""
        CREATE TABLE sparkl2.deposit_addresses (
            id TEXT PRIMARY KEY, wallet_id TEXT NOT NULL, user_id TEXT NOT NULL,
            address TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'issued',
            txid TEXT, amount_sats BIGINT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            claimed_at TIMESTAMP
        );
    """)
    await db.execute("""
        CREATE TABLE sparkl2.transfers (
            id TEXT PRIMARY KEY, wallet_id TEXT NOT NULL, user_id TEXT NOT NULL,
            direction TEXT NOT NULL, amount_sats BIGINT, receiver_address TEXT,
            provider_txid TEXT, status TEXT NOT NULL, provider_response TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

async def m002_add_deposit_index(db):
    await db.execute("CREATE INDEX sparkl2_deposit_wallet ON sparkl2.deposit_addresses(wallet_id)")
    await db.execute("CREATE INDEX sparkl2_deposit_status ON sparkl2.deposit_addresses(status)")
    await db.execute("CREATE INDEX sparkl2_transfer_wallet ON sparkl2.transfers(wallet_id)")
    await db.execute("CREATE INDEX sparkl2_transfer_provider ON sparkl2.transfers(provider_txid)")
