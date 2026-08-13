# SparkL2 Requirements and Acceptance Matrix

## Accounting

- [x] Spark sends debit the selected, ownership-checked LNbits wallet.
- [x] On-chain deposits credit the assigned LNbits wallet.
- [x] Incoming Spark credits use the administrator-selected global wallet.
- [x] Linked/shared wallets are excluded from the global selector.
- [x] Incoming on-chain amounts remain in satoshis.
- [x] LNbits ledger conversion is sats × 1000 msat.
- [x] On-chain withdrawal amount and fee are separate LNbits fields.
- [x] Fee-inclusive balance validation exists.

## Attribution

- [x] Source is persisted separately from transaction type.
- [x] SparkL2 audit source is `#spark-l2`.
- [x] LNbits stored payment tag is `spark-l2` so the UI displays `#spark-l2`.
- [x] Wallet and user attribution are persisted.
- [x] Provider request and on-chain transaction identifiers are preserved.
- [x] Recent Transfers includes local on-chain audit rows.
- [x] Provider/local identifier aliases are merged to avoid duplicate rows.

## Incoming Spark safety

- [x] Direct Spark transfer type is required.
- [x] Incoming direction is required.
- [x] Receiver identity must match the sidecar identity.
- [x] Lightning, swap, cooperative-exit, static-deposit, and unrelated requests are excluded.
- [x] Reconciliation is idempotent by deterministic provider key.

## On-chain receiving

- [x] One-time address assignment is persisted.
- [x] Existing uncredited address is reused instead of generating duplicates.
- [x] Deposit identity includes txid and vout.
- [x] Deposit claiming and crediting are retry-safe.
- [x] Local audit row is created.
- [x] Realtime event is published.

## On-chain sending

- [x] Quote is obtained before submission.
- [x] Nested provider fee fields are normalized.
- [x] Fee is displayed before payment.
- [x] User confirms fee handling.
- [x] Required quote ID and fee amount are submitted.
- [x] Provider `coopExitTxid` is retained when returned.
- [x] Recent Transfers displays a provider transaction ID.

## UI and operations

- [x] Wallet status loads on page entry.
- [x] Recent Transfers loads on page entry.
- [x] SSE refresh is implemented.
- [x] SSE reconnect is implemented.
- [x] Periodic fallback refresh is implemented.
- [x] Administrator-only status and Recent Transfers are protected server-side.
- [ ] Full browser E2E after service restart is still required.
- [ ] Long-run restart/recovery testing is still required.
- [ ] Confirmed on-chain settlement monitoring is still required.

## Verification summary

- Python compile: PASS.
- JavaScript syntax: PASS.
- SparkL2 pytest: PASS, 7 tests.
- Production repairs: performed and verified for known bad deposits and withdrawal accounting.
- Runtime reload: requires administrator restart when source changes are deployed.
