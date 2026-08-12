from ..reconciler import credit_key, parse_utxo


def test_credit_key_is_stable_for_same_output():
    assert credit_key("dep-1", "tx-1", 2) == credit_key("dep-1", "tx-1", 2)


def test_credit_key_separates_outputs():
    assert credit_key("dep-1", "tx-1", 0) != credit_key("dep-1", "tx-1", 1)


def test_parse_utxo_requires_amount_and_output_index():
    assert parse_utxo({"txid": "abc", "vout": 1, "amount_sats": "2500"}) == ("abc", 1, 2500)
