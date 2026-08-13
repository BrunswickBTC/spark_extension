# SparkL2 Extension Architecture

## Scope

SparkL2 is an LNbits extension backed by one authenticated Spark sidecar. It keeps Spark provider identity separate from LNbits accounting identity.

The sidecar owns provider state and the extension owns LNbits wallet attribution, reconciliation, audit records, and UI.

## Components

```text
Browser
  |
  | LNbits.api.request(), authenticated session
  v
LNbits SparkL2 extension
  |-- views.py: extension page
  |-- views_api.py: authenticated API and admin API
  |-- client.py: allowlisted sidecar proxy
  |-- reconciler.py: periodic deposit/transfer reconciliation
  |-- crud.py: extension persistence
  |-- events.py: SSE notifications
  |-- templates/sparkl2/index.html + static/js/index.js
  |
  | authenticated HTTP with server-side API key
  v
Spark sidecar
  |-- Spark SDK wallet
  |-- Spark transfers and identity
  |-- on-chain deposit UTXOs
  |-- withdrawal quotes and cooperative exits
  v
Spark network / Bitcoin indexer

LNbits core database
  |-- wallets / accounts
  |-- apipayments ledger
```

## Identity and attribution model

The sidecar uses one shared Spark identity. LNbits wallets are accounting destinations, not separate Spark wallets.

- User Spark sends: selected LNbits wallet is ownership-checked; the sidecar transaction is attributed to that wallet.
- On-chain receiving: a one-time address is assigned to a selected LNbits wallet before detection.
- Incoming Spark: because the sidecar has one shared receive identity, an administrator selects the global LNbits destination wallet.
- Linked/shared LNbits wallets are excluded from the global receive-wallet selector.

## Data flows

### Incoming on-chain Bitcoin

1. User requests a one-time address for a wallet.
2. Extension persists wallet/user/address with `issued` status.
3. Reconciler asks the sidecar for UTXOs.
4. Sidecar enriches UTXOs from Electrs/mempool and returns `amount_sats`.
5. Reconciler reserves `(deposit_id, txid, vout)`.
6. Sidecar claims the deposit.
7. Extension credits LNbits with `amount_sats * 1000` millisatoshis.
8. Extension marks the address credited.
9. Extension writes a local transfer audit row and publishes an SSE event.

The output identity is `(txid, vout)`, not only `txid`.

### Incoming Spark

Only direct Spark-to-Spark transfers are eligible:

- provider transfer type is `TRANSFER` or equivalent direct Spark type;
- direction is incoming;
- receiver identity exactly matches the sidecar identity;
- Lightning, swap, cooperative-exit, static-deposit, and unrelated request types are excluded.

Credits use deterministic provider-based checking IDs and the administrator-selected global wallet.

### Outgoing Spark

1. API verifies selected wallet ownership.
2. API verifies sufficient LNbits balance.
3. API submits the sidecar transfer.
4. API records the debit and local audit row with source `#spark-l2`.

### Outgoing on-chain Bitcoin

1. User requests a quote with amount, address, and exit speed.
2. API normalizes the raw provider quote into `fee_quote_id` and `fee_amount_sats`.
3. UI displays the fee and asks whether it is deducted from the recipient amount or paid separately.
4. API validates the quote fields and fee-inclusive wallet balance.
5. Sidecar submits the cooperative exit.
6. Local audit stores provider request data and the actual `coopExitTxid` when available.
7. LNbits accounting stores requested amount and fee separately. For a 25,000-sat payment with a 1,470-sat separate fee: amount `-25,000,000 msat`, fee `-1,470,000 msat`.

## Units

- Provider/Electrs UTXO value: satoshis.
- Extension `amount_sats`: satoshis.
- LNbits `apipayments.amount`: millisatoshis.
- Required invariant: `ledger_msat == amount_sats * 1000` for deposits.
- Never multiply an already-satoshi UTXO value by `100_000_000`.

## Persistence

### `sparkl2.settings`

Stores administrator settings such as the global incoming Spark wallet ID.

### `sparkl2.deposit_addresses`

Stores one-time address assignment and reconciliation state, including wallet/user, address, status, txid, vout, amount, and timestamps.

### `sparkl2.transfers`

Stores durable audit attribution:

- direction: `credit` or `debit`;
- transaction_type: `spark` or `onchain`;
- source: `#spark-l2`;
- wallet/user;
- amount in sats;
- provider transaction ID;
- provider response/status;
- created timestamp.

## Idempotency

- Deposit credits are keyed by deposit ID, txid, and vout.
- Spark credits use deterministic checking IDs derived from provider identity.
- Transfer audit rows are checked by provider transaction ID.
- Repairs must target exact checking ID, txid/vout, wallet, and audit row.

## Realtime UI

The extension publishes events through authenticated SSE. The browser refreshes status, transfers, and address state on events, reconnects after errors, and performs a 15-second fallback refresh. Recent Transfers merges provider rows with local audit rows and sorts by normalized creation time.

## Security boundaries

- Sidecar API credentials remain server-side.
- Browser calls use `LNbits.api.request`.
- User APIs verify wallet ownership.
- Administrative APIs require administrator authorization.
- The browser never supplies the trusted amount for automatic deposits.
- Unknown sidecar routes are rejected by the allowlist.

## Deployment boundary

Source files and the running services are separate states. Changes to the extension require an LNbits restart; sidecar source changes require a sidecar restart. The account used during development did not have sudo, so successful compilation/tests do not prove the running services have loaded the latest files.
