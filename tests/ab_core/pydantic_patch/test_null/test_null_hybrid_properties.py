from ab_core.pydantic_patch.null import Null, create_null_model
from tests.ab_core.pydantic_patch.conftest_hybrid_properties import HybridPropertyUser
from tests.helpers.assert_model import assert_field_names


def test_null_includes_hybrid_properties() -> None:
    result = create_null_model(HybridPropertyUser)

    assert_field_names(
        result,
        {
            "id",
            "first_name",
            "last_name",
            "age",
            "full_name",
            "is_adult",
        },
    )


def test_null_generic_api_includes_hybrid_properties() -> None:
    result = Null[HybridPropertyUser]()

    assert_field_names(
        result,
        {
            "id",
            "first_name",
            "last_name",
            "age",
            "full_name",
            "is_adult",
        },
    )


def test_null_validates_and_dumps_hybrid_properties() -> None:
    result = Null[HybridPropertyUser]()

    validated = result.model_validate(
        HybridPropertyUser(
            id=1,
            first_name="Monique",
            last_name="Kuhn",
            age=28,
        )
    )

    assert validated.model_dump() == {
        "id": 1,
        "first_name": "Monique",
        "last_name": "Kuhn",
        "age": 28,
        "full_name": "Monique Kuhn",
        "is_adult": True,
    }