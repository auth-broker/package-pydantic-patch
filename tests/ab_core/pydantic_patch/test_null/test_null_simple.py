from pydantic import BaseModel

from ab_core.pydantic_patch.null import Null, create_null_model
from tests.helpers.assert_model import assert_field_names


class NullSimpleUser(BaseModel):
    id: int
    name: str
    email: str | None = None


def test_null_creates_plain_pydantic_model_with_same_fields() -> None:
    result = create_null_model(NullSimpleUser)

    assert issubclass(result, BaseModel)
    assert result is not NullSimpleUser
    assert result.__name__ == "NullSimpleUserNull"

    assert_field_names(result, {"id", "name", "email"})


def test_null_generic_api() -> None:
    result = Null[NullSimpleUser]()

    assert issubclass(result, BaseModel)
    assert_field_names(result, {"id", "name", "email"})


def test_null_custom_name() -> None:
    result = create_null_model(
        NullSimpleUser,
        name="NullSimpleUserResponse",
    )

    assert result.__name__ == "NullSimpleUserResponse"


def test_null_repeated_same_config_returns_same_type() -> None:
    result_a = create_null_model(NullSimpleUser)
    result_b = create_null_model(NullSimpleUser)

    assert result_a is result_b


def test_null_different_custom_name_returns_different_type() -> None:
    result_a = create_null_model(
        NullSimpleUser,
        name="NullSimpleUserResponseA",
    )
    result_b = create_null_model(
        NullSimpleUser,
        name="NullSimpleUserResponseB",
    )

    assert result_a is not result_b
    assert result_a.__name__ == "NullSimpleUserResponseA"
    assert result_b.__name__ == "NullSimpleUserResponseB"


def test_null_validates_source_model_instance() -> None:
    result = Null[NullSimpleUser]()

    validated = result.model_validate(
        NullSimpleUser(
            id=1,
            name="Monique",
            email="monique@example.com",
        )
    )

    assert validated.model_dump() == {
        "id": 1,
        "name": "Monique",
        "email": "monique@example.com",
    }


def test_null_validates_dict_payload() -> None:
    result = Null[NullSimpleUser]()

    validated = result.model_validate(
        {
            "id": 1,
            "name": "Monique",
            "email": None,
        }
    )

    assert validated.id == 1
    assert validated.name == "Monique"
    assert validated.email is None
