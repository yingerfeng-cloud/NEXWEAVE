import pytest

from nexweave_api.errors import ApiProblem
from nexweave_api.settings import Settings
from nexweave_api.workflow_gateway import TemporalWorkflowGateway


@pytest.mark.parametrize(
    "failure", [RuntimeError("DNS connection unavailable"), ConnectionError("refused")]
)
async def test_initial_temporal_connection_failure_is_a_safe_retryable_problem(
    monkeypatch, failure
):
    async def unavailable(*args, **kwargs):
        raise failure

    monkeypatch.setattr("nexweave_api.workflow_gateway.Client.connect", unavailable)
    gateway = TemporalWorkflowGateway(Settings())
    with pytest.raises(ApiProblem) as raised:
        await gateway.connect()
    assert raised.value.status == 503
    assert raised.value.code == "WORKFLOW_DEPENDENCY_UNAVAILABLE"
    assert "DNS" not in str(raised.value)
    assert gateway._client is None
