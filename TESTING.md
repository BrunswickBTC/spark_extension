# SparkL2 Testing and Verification

## Commands

Run from `/var/lib/lnbits/lnbits`:

```bash
python -m compileall -q lnbits/extensions/sparkl2
node --check lnbits/extensions/sparkl2/static/js/index.js
/var/lib/lnbits/.local/bin/uv run --with pytest pytest -q lnbits/extensions/sparkl2/tests
```

## Current automated result

Verified on the deployed checkout:

- Python compilation: **PASS**
- JavaScript syntax check: **PASS**
- Pytest: **PASS — 7 passed, 1 coverage warning**

The warning was a missing optional coverage C tracer and did not fail the suite.

## Automated coverage currently present

### Client route allowlist

- Unknown sidecar route rejected.
- Balance route maps to `POST /v1/balance`.
- Identity/settings/optimization routes map correctly.
- Deposit and transfer-list routes map correctly.

### Router and model compatibility

- SparkL2 router imports and can be included in a FastAPI router.
- Pydantic model serialization works through the compatibility helper.

### Reconciliation primitives

- Deposit credit key is stable for the same deposit/txid/vout.
- Different outputs receive different keys.
- UTXO parsing requires txid, output index, and amount.

## Production verification performed

The following behaviors were verified through live database/provider evidence during development:

- Direct Spark receiving was narrowed from broad incoming matching to exact destination identity matching.
- Historical bogus Spark receive credits were identified by generated checking-ID namespace and removed.
- Linked/shared wallets were excluded from global receive-wallet selection.
- An erroneous 19,335-sat deposit inflated by `100_000_000` was repaired.
- A later 100,000-sat deposit inflated by `100_000_000` was repaired.
- On-chain deposit records preserve txid and vout.
- Incoming on-chain credits are represented in local Recent Transfers audit rows.
- Recent Transfers merges local audit rows with provider rows and sorts by normalized creation time.
- Realtime SSE refresh plus periodic fallback was implemented.
- An on-chain withdrawal quote was normalized from nested SDK fee fields.
- A 25,000-sat withdrawal with a 1,470-sat fee was repaired to amount `25,000 sats`, fee `1,470 sats`, total debit `26,470 sats`.
- The withdrawal audit stores the actual provider `coopExitTxid`.
- Payment tags were corrected from stored `#spark-l2` to stored `spark-l2` so the LNbits UI displays one hash mark.

## Required regression tests to add

The existing suite is too small for the financial behavior. Add tests for:

1. UTXO amount `100000` remains `100000`.
2. A malformed `10000000000000` value is normalized/rejected safely.
3. Ledger deposit amount equals `amount_sats * 1000`.
4. Deposit reconciliation is idempotent for the same txid/vout.
5. Unrelated incoming Lightning rows are ignored.
6. Unrelated incoming Bitcoin/on-chain rows are ignored.
7. Direct incoming Spark to the shared identity is credited.
8. Spark transfer to another identity is ignored.
9. Linked/shared global wallets are rejected.
10. Spark sends enforce wallet balance before provider submission.
11. On-chain withdrawals enforce fee-inclusive balance.
12. Quote normalization extracts fee and quote ID from all supported SDK shapes.
13. Fee-deducted and fee-paid-separately withdrawals compute correct wallet debit.
14. `coopExitTxid` is persisted and displayed.
15. Request ID and transaction ID aliases deduplicate to one Recent Transfers row.
16. Local on-chain audit rows appear when absent from the provider transfer list.
17. Local and provider rows sort newest-first.
18. SSE event refreshes balance, transfers, and address state.
19. SSE reconnect and 15-second fallback refresh work.
20. Exact financial repair targets only the intended checking ID and audit row.

## Manual end-to-end checklist

After restarting services:

1. Open the SparkL2 extension as an administrator.
2. Confirm wallet status loads without manual refresh.
3. Send a small Spark amount and confirm one debit and one audit row.
4. Generate a one-time on-chain receive address.
5. Send a known small amount.
6. Confirm sidecar delta is in sats.
7. Confirm LNbits delta is `sats * 1000` msat.
8. Confirm Recent Transfers shows one credit with txid:vout.
9. Confirm the UI updates without a page refresh.
10. Request an on-chain withdrawal quote.
11. Confirm the fee is numeric and visible.
12. Confirm fee handling explicitly.
13. Submit only after confirmation.
14. Confirm LNbits amount and fee are separate.
15. Confirm Recent Transfers shows one row and the provider/on-chain ID.
16. Query the provider/indexer to confirm the transaction status independently.

## Not yet proven by the automated suite

- Full browser-rendered UI behavior after a service restart.
- Full SSE behavior through every proxy/browser combination.
- Successful on-chain settlement/confirmation after submission.
- Long-running reconciler behavior across process restarts.
- Live quote expiry and retry behavior.
