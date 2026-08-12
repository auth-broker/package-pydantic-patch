import pytest

from pydantic_patch.core.errors import ForwardReferencesNotSupported
from pydantic_patch.null import Null
from pydantic_patch.omit import Omit
from pydantic_patch.partial import Partial
from pydantic_patch.patch import Patch
from pydantic_patch.pick import Pick
from pydantic_patch.required import Required
from tests.pydantic_patch.conftest_hybrid_properties import (
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
