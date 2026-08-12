from ..models import TransfersRequest
from ..views_api import _model_data


def test_model_data_supports_pydantic_v1():
    data = TransfersRequest(limit=100, offset=0)
    assert _model_data(data, exclude_none=True) == {"limit": 100, "offset": 0}
