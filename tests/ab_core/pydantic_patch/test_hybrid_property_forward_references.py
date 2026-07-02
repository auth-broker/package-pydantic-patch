import pytest

from ab_core.pydantic_patch.core.errors import ForwardReferencesNotSupported
from ab_core.pydantic_patch.null import Null
from ab_core.pydantic_patch.omit import Omit
from ab_core.pydantic_patch.partial import Partial
from ab_core.pydantic_patch.patch import Patch
from ab_core.pydantic_patch.pick import Pick
from ab_core.pydantic_patch.required import Required
from tests.ab_core.pydantic_patch.conftest_hybrid_properties import (
    HybridPropertyForwardRefModel,
)


@pytest.mark.parametrize(
    "operation",
    [
        lambda: Pick[HybridPropertyForwardRefModel](fields={"manager"}),
        lambda: Omit[HybridPropertyForwardRefModel](fields=set()),
        lambda: Partial[HybridPropertyForwardRefModel](fields={"manager"}),
        lambda: Required[HybridPropertyForwardRefModel](fields={"manager"}),
        lambda: Patch[HybridPropertyForwardRefModel](pick={"manager"}),
        lambda: Null[HybridPropertyForwardRefModel](),
    ],
)
def test_hybrid_property_forward_ref_raises_custom_error(operation) -> None:
    with pytest.raises(ForwardReferencesNotSupported, match="manager"):
        operation()