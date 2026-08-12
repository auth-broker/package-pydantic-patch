import pytest

from pydantic_patch.core.errors import ConflictingPatchConfigError
from pydantic_patch.patch import PatchConfig, create_patch_model
from tests.pydantic_patch.conftest_hybrid_properties import HybridPropertyUser


def test_required_hybrid_property_not_in_payload_raises() -> None:
    with pytest.raises(ConflictingPatchConfigError):
        create_patch_model(
            HybridPropertyUser,
            config=PatchConfig(
                pick={"first_name"},
                required={"full_name"},
            ),
        )


def test_partial_hybrid_property_not_in_payload_raises() -> None:
    with pytest.raises(ConflictingPatchConfigError):
        create_patch_model(
            HybridPropertyUser,
            config=PatchConfig(
                omit={"full_name"},
                partial={"full_name"},
            ),
        )
