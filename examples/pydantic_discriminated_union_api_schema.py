from collections.abc import Mapping
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Discriminator

from ab_core.pydantic_patch.patch import Patch, PatchConfig

ENTITY_ID = 0


# =========================
# MODELS
# =========================


class Cat(BaseModel):
    kind: Literal["cat"]
    id: int
    name: str
    lives: int


class Dog(BaseModel):
    kind: Literal["dog"]
    id: int
    name: str
    bark_volume: int


Pet = Annotated[Cat | Dog, Discriminator("kind")]


class Household(BaseModel):
    id: int
    owner_name: str
    pets: list[Pet]


# =========================
# PATCH MODEL
# =========================

HouseholdPatch = Patch[Household](
    pick={"owner_name", "pets"},
    child_models={
        Cat: PatchConfig(
            pick={"kind", "id", "name"},  # cannot edit lives
            required={"kind", "id"},
        ),
        Dog: PatchConfig(
            pick={"kind", "id", "name"},  # cannot edit bark_volume
            required={"kind", "id"},
        ),
    },
)


# =========================
# FAKE STORE
# =========================

HOUSEHOLDS: dict[int, Household] = {}


def seed() -> None:
    HOUSEHOLDS.setdefault(
        ENTITY_ID,
        Household(
            id=ENTITY_ID,
            owner_name="Monique",
            pets=[
                Cat(kind="cat", id=10, name="Mimi", lives=9),
                Dog(kind="dog", id=20, name="Scout", bark_volume=5),
            ],
        ),
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed()
    yield


app = FastAPI(lifespan=lifespan)


# =========================
# UPDATE HELPERS
# =========================


def apply_scalar_patch(instance: BaseModel, data: Mapping[str, object]) -> None:
    for field_name, value in data.items():
        if field_name in {"id", "kind"}:
            continue

        setattr(instance, field_name, value)


def apply_pet_patch(household: Household, pet_data: Mapping[str, object]) -> None:
    pet_id = pet_data["id"]
    pet_kind = pet_data["kind"]

    pet = next(
        (
            existing_pet
            for existing_pet in household.pets
            if existing_pet.id == pet_id and existing_pet.kind == pet_kind
        ),
        None,
    )

    if pet is None:
        raise HTTPException(status_code=404, detail=f"{pet_kind.title()} not found")

    apply_scalar_patch(pet, pet_data)


# =========================
# API
# =========================


@app.get("/households", response_model=Household)
def get_household() -> Household:
    household = HOUSEHOLDS.get(ENTITY_ID)
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")

    return household


@app.patch("/households", response_model=Household)
def patch_household(
    patch: HouseholdPatch,
) -> Household:
    household = HOUSEHOLDS.get(ENTITY_ID)
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")

    data = patch.model_dump(exclude_unset=True)

    household_data = {key: value for key, value in data.items() if key != "pets"}
    apply_scalar_patch(household, household_data)

    for pet_data in data.get("pets", []):
        apply_pet_patch(household, pet_data)

    return household


# =========================
# RUN
# =========================

if __name__ == "__main__":
    import uvicorn

    # http://localhost:8000/docs#/default/patch_household_households__household_id__patch
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
