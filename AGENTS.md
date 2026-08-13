# SparkL2 Agent and Contributor Instructions

## Mission

Preserve correct attribution and accounting between LNbits, the Spark sidecar, and Bitcoin. Financial correctness takes priority over convenience.

## Required design rules

1. Keep provider identity separate from LNbits wallet identity.
2. Keep all SparkL2 behavior inside the extension unless a core integration is explicitly requested.
3. Never credit incoming Spark funds based only on an incoming status or a generic provider transfer list.
4. Require exact destination identity for shared Spark receiving.
5. Treat Electrs/mempool UTXO values as satoshis in this deployment.
6. Convert sats to millisatoshis exactly once when writing the LNbits ledger.
7. Persist `direction`, `transaction_type`, and `source` separately.
8. Store LNbits payment tags as `spark-l2`; LNbits adds the display `#`.
9. Use deterministic idempotency keys and preserve provider IDs.
10. For on-chain withdrawals, quote first, show the fee, confirm fee handling, then submit.
11. Store withdrawal amount and fee in separate LNbits fields.
12. Include the actual on-chain transaction ID (`coopExitTxid`) when the provider returns it.
13. Do not bulk-edit or bulk-delete financial records. Repair exact rows only.
14. Verify ownership and balance before contacting the provider.
15. Keep sidecar credentials out of browser code and logs.

## Files

- `client.py`: sidecar route allowlist and authenticated HTTP client.
- `views.py`: extension page.
- `views_api.py`: API routes, authorization, quote normalization, transfer display.
- `models.py`: request validation.
- `crud.py`: extension persistence.
- `reconciler.py`: periodic credits, idempotency, unit checks, SSE publication.
- `events.py`: SSE event stream.
- `migrations.py`: extension schema and repair migrations.
- `templates/sparkl2/index.html`: UI.
- `static/js/index.js`: UI state, quote flow, realtime refresh.
- `tests/`: automated tests.

## Change workflow

1. Inspect the live code and provider payload before editing.
2. Identify the boundary: provider, sidecar, extension, LNbits ledger, or UI.
3. Add or update a focused test before changing financial logic.
4. Make the smallest reversible change.
5. Compile Python and check JavaScript syntax.
6. Run the complete SparkL2 test suite.
7. Inspect exact database rows for any repair.
8. Deploy source files.
9. State explicitly whether a service restart was performed.
10. Verify the loaded service and UI separately from source verification.

## Financial repair rules

Before a repair, identify:

- wallet ID and wallet name;
- checking ID;
- provider ID and transaction ID;
- txid/vout for on-chain deposits;
- amount and fee units;
- memo and source;
- matching SparkL2 audit row.

Use one transaction where practical. Do not issue a compensating credit when the original row can be corrected. Afterward verify the LNbits amount, fee, extension amount, provider amount, and audit linkage.

## Do not claim

- Do not claim a service restart without command output.
- Do not claim browser verification from Python tests.
- Do not claim a provider transaction is confirmed merely because a request was submitted.
- Do not call a provider status a transaction ID.
- Do not call source deployment a loaded runtime.
