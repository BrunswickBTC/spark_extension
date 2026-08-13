# SparkL2 LNbits Extension

SparkL2 integrates a shared Spark sidecar with LNbits accounting while preserving wallet attribution, idempotent reconciliation, on-chain deposit handling, withdrawal fee accounting, and administrator audit visibility.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Agent/contributor instructions](AGENTS.md)
- [Requirements and acceptance matrix](REQUIREMENTS.md)
- [Testing and verification](TESTING.md)
- [Operations and incident runbook](OPERATIONS.md)

## Verification status

The deployed extension currently passes:

```text
Python compilation: PASS
JavaScript syntax: PASS
Pytest: 7 passed
```

The documentation distinguishes source/test verification from loaded-service and browser verification. Restart LNbits after extension changes and restart the sidecar after sidecar changes.

## Core accounting contract

- Provider and extension amounts are satoshis.
- LNbits ledger amounts are millisatoshis.
- Deposit invariant: `ledger_msat = amount_sats * 1000`.
- Withdrawal amount and fee are separate LNbits fields.
- Direct incoming Spark transfers require exact receiver identity matching.
