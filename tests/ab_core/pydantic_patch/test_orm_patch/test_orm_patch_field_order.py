from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from ab_core.pydantic_patch.orm_patch import _identity_tuple, _primary_key_names, _provided_values


class PatchModel(BaseModel):
    category: str | None = None
    line_item_name: str | None = None
    additional_description: str | None = None
    unit: str | None = None
    quantity: float | None = None
    quoted_base_cost: float | None = None
    children: list[str] | None = None


class CompositePrimaryKeyModel(SQLModel, table=True):
    __tablename__ = "test_composite_primary_key_order"

    account_id: int | None = Field(default=None, primary_key=True)
    line_item_id: int | None = Field(default=None, primary_key=True)
    name: str = ""


def test_provided_values_uses_model_field_order() -> None:
    patch = PatchModel(
        category="Timber Fencing",
        line_item_name="New timber paling fence",
        additional_description="Rear boundary",
        unit="lm",
        quantity=22.0,
        quoted_base_cost=0.0,
        children=["demo", "install"],
    )

    assert list(_provided_values(patch)) == [
        "category",
        "line_item_name",
        "additional_description",
        "unit",
        "quantity",
        "quoted_base_cost",
        "children",
    ]


def test_primary_key_identity_uses_mapper_primary_key_order() -> None:
    pk_names = _primary_key_names(CompositePrimaryKeyModel)
    instance = CompositePrimaryKeyModel(account_id=7, line_item_id=11)

    assert pk_names == ("account_id", "line_item_id")
    assert _identity_tuple(instance, pk_names) == (7, 11)
