

from datetime import datetime
from typing import Annotated, Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, Discriminator


class User(BaseModel):
    id: int | None = None
    name: str
    email: str
    created_at: datetime
    updated_at: datetime


class Address(BaseModel):
    id: int | None = None
    line_1: str
    line_2: str | None = None
    suburb: str
    postcode: str
    created_at: datetime
    updated_at: datetime


class Customer(BaseModel):
    id: int | None = None
    name: str
    address: Address
    billing_address: Address


class Organisation(BaseModel):
    id: int | None = None
    name: str
    primary_address: Address
    postal_address: Address
    branch_addresses: list[Address]
    address_lookup: dict[str, Address]
    created_at: datetime
    updated_at: datetime


class BenchmarkMatch(BaseModel):
    id: int | None = None
    category: str
    line_item_name: str
    selected: bool
    match_score: float
    created_at: datetime
    updated_at: datetime


class QuoteLineItem(BaseModel):
    id: int | None = None
    description: str
    quantity: float
    unit: str
    benchmark_matches: list[BenchmarkMatch]
    created_at: datetime
    updated_at: datetime


class Quote(BaseModel):
    id: int | None = None
    quote_number: str
    line_items: list[QuoteLineItem]
    created_at: datetime
    updated_at: datetime


class Cat(BaseModel):
    kind: Literal["cat"] = "cat"
    id: int | None = None
    lives: int
    name: str
    secret_tracking_code: str


class Dog(BaseModel):
    kind: Literal["dog"] = "dog"
    id: int | None = None
    bark_volume: int
    name: str
    secret_tracking_code: str


class Bird(BaseModel):
    kind: Literal["bird"] = "bird"
    id: int | None = None
    wing_span: float
    name: str
    secret_tracking_code: str


Pet = Annotated[Cat | Dog | Bird, Discriminator("kind")]


class PetOwner(BaseModel):
    id: int | None = None
    name: str
    pet: Pet
    previous_pets: list[Pet]
    created_at: datetime
    updated_at: datetime


class ArbitraryPayload(BaseModel):
    id: int
    metadata: dict[str, object]
    raw_value: object


class MixedUnionPayload(BaseModel):
    id: int
    value: Address | str


@pytest.fixture

def models():
    return {
        "User": User,
        "Address": Address,
        "Customer": Customer,
        "Organisation": Organisation,
        "BenchmarkMatch": BenchmarkMatch,
        "QuoteLineItem": QuoteLineItem,
        "Quote": Quote,
        "Cat": Cat,
        "Dog": Dog,
        "Bird": Bird,
        "PetOwner": PetOwner,
        "ArbitraryPayload": ArbitraryPayload,
        "MixedUnionPayload": MixedUnionPayload,
    }


# -----------------------------------------------------------------------------
# Expected model fixtures
# -----------------------------------------------------------------------------


class UserNameEmailPickExpected(BaseModel):
    name: str
    email: str


class UserEmptyPickExpected(BaseModel):
    pass


class UserOmitAuditExpected(BaseModel):
    id: int | None = None
    name: str
    email: str


class UserPartialAllExpected(BaseModel):
    id: int | None = None
    name: str | None = None
    email: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserPartialNameExpected(BaseModel):
    id: int | None = None
    name: str | None = None
    email: str
    created_at: datetime
    updated_at: datetime


class UserRequiredIdExpected(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: datetime


class UserPatchIdNameEmailExpected(BaseModel):
    id: int
    name: str | None = None
    email: str | None = None


class AddressPickSuburbPostcodeExpected(BaseModel):
    suburb: str
    postcode: str


class AddressOmitAuditExpected(BaseModel):
    id: int | None = None
    line_1: str
    line_2: str | None = None
    suburb: str
    postcode: str


class AddressPartialAllExpected(BaseModel):
    id: int | None = None
    line_1: str | None = None
    line_2: str | None = None
    suburb: str | None = None
    postcode: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AddressRequiredIdExpected(BaseModel):
    id: int
    line_1: str
    line_2: str | None = None
    suburb: str
    postcode: str
    created_at: datetime
    updated_at: datetime


@pytest.fixture

def expected_models():
    return {
        "UserNameEmailPickExpected": UserNameEmailPickExpected,
        "UserEmptyPickExpected": UserEmptyPickExpected,
        "UserOmitAuditExpected": UserOmitAuditExpected,
        "UserPartialAllExpected": UserPartialAllExpected,
        "UserPartialNameExpected": UserPartialNameExpected,
        "UserRequiredIdExpected": UserRequiredIdExpected,
        "UserPatchIdNameEmailExpected": UserPatchIdNameEmailExpected,
        "AddressPickSuburbPostcodeExpected": AddressPickSuburbPostcodeExpected,
        "AddressOmitAuditExpected": AddressOmitAuditExpected,
        "AddressPartialAllExpected": AddressPartialAllExpected,
        "AddressRequiredIdExpected": AddressRequiredIdExpected,
    }
