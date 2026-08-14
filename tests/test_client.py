import pytest

from ..client import sidecar_path


def test_sidecar_path_rejects_unknown_route():
    with pytest.raises(ValueError, match="Unsupported Spark sidecar route"):
        sidecar_path("unknown")


def test_sidecar_path_maps_read_only_routes():
    assert sidecar_path("capabilities") == ("GET", "/v1/capabilities")
    assert sidecar_path("balance") == ("POST", "/v1/balance")
    assert sidecar_path("identity") == ("GET", "/v1/identity")
    assert sidecar_path("settings") == ("GET", "/v1/settings")
    assert sidecar_path("optimization") == ("POST", "/v1/status/optimization")
    assert sidecar_path("single_use_deposit") == ("GET", "/v1/deposit/single-use")
    assert sidecar_path("static_deposit") == ("GET", "/v1/deposit/static")
    assert sidecar_path("static_addresses") == ("GET", "/v1/deposit/static/addresses")
    assert sidecar_path("transfers") == ("POST", "/v1/transfers/list")
