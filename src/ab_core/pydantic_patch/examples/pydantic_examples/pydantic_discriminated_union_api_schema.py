from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Discriminator

from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar
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
            required={"kind"},
        ),
        Dog: PatchConfig(
            pick={"kind", "id", "name"},  # cannot edit bark_volume
            required={"kind"},
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

    recursive_patch_orm_scalar(household, patch)

    return household


# =========================
# RUN
# =========================


def get_module_path(file_path: str) -> str:
    parts = Path(file_path).resolve().with_suffix("").relative_to(Path.cwd()).parts

    if parts[0] == "src":
        parts = parts[1:]

    return ".".join(parts)


if __name__ == "__main__":
    import uvicorn

    # http://localhost:8000/docs#/default/patch_household_households__household_id__patch
    uvicorn.run(
        f"{get_module_path(__file__)}:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
