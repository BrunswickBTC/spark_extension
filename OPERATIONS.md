# SparkL2 Operations and Incident Runbook

## Services

```bash
sudo systemctl restart spark-sidecar.service
sudo systemctl restart lnbits.service
```

Restart the sidecar after `/var/lib/spark_sidecar/server.mjs` changes. Restart LNbits after extension Python/template/static changes.

The development account did not have sudo. Source installation and test success therefore did not prove the runtime had reloaded the latest files.

## Logs

```bash
journalctl -u lnbits.service -f
journalctl -u spark-sidecar.service -f
```

Useful SparkL2 log phrases:

```text
Spark receive reconciliation
Credited incoming Spark transfer
Spark on-chain reconciliation failed
Skipping Spark transfer
```

## Database evidence

Always identify exact rows before repair:

```sql
SELECT checking_id, wallet_id, amount, fee, memo, tag, status, time
FROM apipayments
WHERE checking_id = '<checking-id>';

SELECT id, wallet_id, user_id, txid, vout, amount_sats, status
FROM sparkl2.deposit_addresses
WHERE txid = '<txid>' AND vout = <vout>;

SELECT id, wallet_id, direction, transaction_type, source,
       amount_sats, provider_txid, status, created_at
FROM sparkl2.transfers
WHERE provider_txid = '<provider-id>';
```

## Unit checks

For an on-chain deposit:

```text
provider amount in sats       = N
extension amount_sats         = N
LNbits amount in msat          = N * 1000
```

For a withdrawal:

```text
recipient amount               = requested amount
fee                            = provider fee
wallet debit                   = amount + fee when fee is separate
LNbits amount                  = -amount * 1000
LNbits fee                     = -fee * 1000
```

## Repair procedure

1. Stop or disable the faulty reconciliation path if it is still crediting bad rows.
2. Capture txid/vout or provider ID.
3. Identify exact LNbits checking ID.
4. Identify exact extension deposit/audit row.
5. Verify provider amount independently.
6. Repair ledger, extension metadata, and audit linkage together.
7. Verify no duplicate credit exists.
8. Compile and run tests.
9. Restart the appropriate service.
10. Verify the loaded runtime and UI.

Never use a broad amount-only delete or update.

## Known historical incidents

### Broad incoming transfer matching

Historical provider rows were incorrectly treated as incoming credits. The fix requires direct Spark transfer type, incoming direction, exact receiver identity, and exclusion of Lightning, swap, exit, and deposit-request variants.

### Satoshi inflation

Two deposits were observed with a `100_000_000` multiplier. The sidecar contract is satoshis, and the reconciler now applies a supply-bound validation/normalization guard. Verify every future deposit at provider, extension, and LNbits levels.

### Missing Recent Transfers row

The reconciler once queried `apipayments.wallet`; the deployed schema uses `wallet_id`. The lookup is now corrected. Local on-chain audit rows must be displayed even if absent from the provider Spark transfer list.

### On-chain withdrawal fee accounting

The provider response may contain an opaque request ID and a separate actual `coopExitTxid`. Recent Transfers must display the actual transaction ID when returned. LNbits amount and fee must remain separate.

## Safety

- Do not expose sidecar credentials.
- Do not paste full provider responses containing secrets or signing material into public tickets.
- Redact raw connector transactions, secret ciphertexts, signatures, and API keys.
- Do not restart services blindly during an active payment incident without checking status and logs.
