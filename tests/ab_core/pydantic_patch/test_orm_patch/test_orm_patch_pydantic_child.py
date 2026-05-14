from pydantic import BaseModel
from sqlalchemy import Column
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


class QuoteWithAddress(SQLModel, table=True):
    __tablename__ = "test_quote_with_address"

    id: int | None = Field(default=None, primary_key=True)
    claim_number: str = ""

    supplier_address: SupplierAddress = Field(
        default_factory=SupplierAddress,
        sa_column=Column(PydanticJSONB(SupplierAddress), nullable=False),
    )


QuoteWithAddressPatch = Patch[QuoteWithAddress](
    pick={"id", "supplier_address"},
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
    },
)


def test_recursive_patch_orm_scalar_recursively_patches_pydantic_jsonb_scalar() -> None:
    quote = QuoteWithAddress(
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

    patch = QuoteWithAddressPatch(
        id=1,
        supplier_address={
            "state": "VIC",
        },
    )

    recursive_patch_orm_scalar(quote, patch)

    assert isinstance(quote.supplier_address, SupplierAddress)
    assert quote.supplier_address.address_line_1 == "363 George St"
    assert quote.supplier_address.address_line_2 == "Level 2"
    assert quote.supplier_address.suburb == "Sydney"
    assert quote.supplier_address.state == "VIC"
    assert quote.supplier_address.postcode == "2000"


def test_recursive_patch_orm_scalar_ignores_parent_primary_key() -> None:
    quote = QuoteWithAddress(
        id=1,
        supplier_address=SupplierAddress(state="NSW"),
    )

    patch = QuoteWithAddressPatch(
        id=999,
        supplier_address={"state": "VIC"},
    )

    recursive_patch_orm_scalar(quote, patch)

    assert quote.id == 1
    assert quote.supplier_address.state == "VIC"
