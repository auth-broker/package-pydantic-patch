from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm.attributes import set_committed_value
from sqlmodel import Field, SQLModel

from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar
from ab_core.pydantic_patch.patch import Patch, PatchConfig
from ab_core.pydantic_patch.pydantic_jsonb import PydanticJSONB


class SupplierAddress(BaseModel):
    address_line_1: str = ""
    address_line_2: str = ""
    suburb: str = ""
    state: str = ""
    postcode: str = ""


class SupplierContact(BaseModel):
    name: str = ""
    phone: str = ""


class QuoteWithJsonColumns(SQLModel, table=True):
    __tablename__ = "test_quote_with_json_columns"

    id: int | None = Field(default=None, primary_key=True)
    claim_number: str = ""

    supplier_address: SupplierAddress = Field(
        default_factory=SupplierAddress,
        sa_column=Column(PydanticJSONB(SupplierAddress), nullable=False),
    )

    supplier_contacts: list[SupplierContact] = Field(
        default_factory=list,
        sa_column=Column(PydanticJSONB(list[SupplierContact]), nullable=False),
    )

    supplier_metadata: dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(PydanticJSONB(dict[str, str]), nullable=False),
    )


QuoteWithJsonColumnsPatch = Patch[QuoteWithJsonColumns](
    pick={
        "id",
        "supplier_address",
        "supplier_contacts",
        "supplier_metadata",
    },
    required={"id"},
    child_models={
        SupplierAddress: PatchConfig(
            pick={
                "address_line_1",
                "address_line_2",
                "suburb",
                "state",
                "postcode",
            },
            partial=None,
        ),
        SupplierContact: PatchConfig(
            pick={"name", "phone"},
            partial=None,
        ),
    },
)


def mark_column_clean(instance: SQLModel, key: str) -> None:
    set_committed_value(instance, key, getattr(instance, key))


def assert_column_dirty(instance: SQLModel, key: str) -> None:
    history = sa_inspect(instance).attrs[key].history
    assert history.has_changes()


def test_recursive_patch_orm_scalar_recursively_patches_pydantic_jsonb_scalar_and_marks_dirty() -> None:
    quote = QuoteWithJsonColumns(
        id=1,
        claim_number="CLM-001",
        supplier_address=SupplierAddress(
            address_line_1="363 George St",
            address_line_2="Level 2",
            suburb="Sydney",
            state="NSW",
            postcode="2000",
        ),
    )
    mark_column_clean(quote, "supplier_address")

    patch = QuoteWithJsonColumnsPatch(
        id=1,
        supplier_address={"state": "VIC"},
    )

    recursive_patch_orm_scalar(quote, patch)

    assert isinstance(quote.supplier_address, SupplierAddress)
    assert quote.supplier_address.address_line_1 == "363 George St"
    assert quote.supplier_address.address_line_2 == "Level 2"
    assert quote.supplier_address.suburb == "Sydney"
    assert quote.supplier_address.state == "VIC"
    assert quote.supplier_address.postcode == "2000"
    assert_column_dirty(quote, "supplier_address")


def test_recursive_patch_orm_scalar_ignores_parent_primary_key_and_marks_jsonb_scalar_dirty() -> None:
    quote = QuoteWithJsonColumns(
        id=1,
        supplier_address=SupplierAddress(state="NSW"),
    )
    mark_column_clean(quote, "supplier_address")

    patch = QuoteWithJsonColumnsPatch(
        id=999,
        supplier_address={"state": "VIC"},
    )

    recursive_patch_orm_scalar(quote, patch)

    assert quote.id == 1
    assert quote.supplier_address.state == "VIC"
    assert_column_dirty(quote, "supplier_address")


def test_recursive_patch_orm_scalar_patches_pydantic_jsonb_list_and_marks_dirty() -> None:
    quote = QuoteWithJsonColumns(
        id=1,
        supplier_contacts=[
            SupplierContact(name="Alice", phone="111"),
        ],
    )
    mark_column_clean(quote, "supplier_contacts")

    patch = QuoteWithJsonColumnsPatch(
        id=1,
        supplier_contacts=[
            {"name": "Bob", "phone": "222"},
        ],
    )

    recursive_patch_orm_scalar(quote, patch)

    assert len(quote.supplier_contacts) == 1
    assert quote.supplier_contacts[0].name == "Bob"
    assert quote.supplier_contacts[0].phone == "222"
    assert_column_dirty(quote, "supplier_contacts")


def test_recursive_patch_orm_scalar_patches_pydantic_jsonb_dict_and_marks_dirty() -> None:
    quote = QuoteWithJsonColumns(
        id=1,
        supplier_metadata={
            "source": "extraction",
            "status": "draft",
        },
    )
    mark_column_clean(quote, "supplier_metadata")

    patch = QuoteWithJsonColumnsPatch(
        id=1,
        supplier_metadata={
            "source": "manual",
            "status": "reviewed",
        },
    )

    recursive_patch_orm_scalar(quote, patch)

    assert quote.supplier_metadata == {
        "source": "manual",
        "status": "reviewed",
    }
    assert_column_dirty(quote, "supplier_metadata")
