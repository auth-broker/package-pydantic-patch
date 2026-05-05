from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException
from pydantic import Discriminator
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select

from ab_core.pydantic_patch.patch import PatchConfig, create_patch_model


class CatProfile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    lives: int
    indoor_only: bool = False
    household_id: int | None = Field(default=None, foreign_key="household.id")


class DogProfile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    bark_volume: int
    trained: bool = False
    household_id: int | None = Field(default=None, foreign_key="household.id")


class Toy(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    favourite: bool = False
    household_id: int | None = Field(default=None, foreign_key="household.id")


class Household(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_name: str
    address: str

    cats: list[CatProfile] = Relationship()
    dogs: list[DogProfile] = Relationship()
    toys: list[Toy] = Relationship()


class CatPatch(SQLModel):
    kind: Literal["cat"]
    id: int
    name: str
    lives: int
    indoor_only: bool


class DogPatch(SQLModel):
    kind: Literal["dog"]
    id: int
    name: str
    bark_volume: int
    trained: bool


PetPatch = Annotated[CatPatch | DogPatch, Discriminator("kind")]


class HouseholdPatchEnvelope(SQLModel):
    household: Household
    featured_pet: PetPatch | None = None


HouseholdPatchRequest = create_patch_model(
    HouseholdPatchEnvelope,
    pick={"household", "featured_pet"},
    child_models={
        Household: PatchConfig(
            pick={"id", "owner_name", "address", "cats", "dogs", "toys"},
            required={"id"},
            child_models={
                CatProfile: PatchConfig(
                    pick={"id", "name", "lives", "indoor_only"},
                    required={"id"},
                ),
                DogProfile: PatchConfig(
                    pick={"id", "name", "bark_volume", "trained"},
                    required={"id"},
                ),
                Toy: PatchConfig(
                    pick={"id", "name", "favourite"},
                    required={"id"},
                ),
            },
        ),
        CatPatch: PatchConfig(
            pick={"kind", "id", "name", "lives", "indoor_only"},
            required={"kind", "id"},
        ),
        DogPatch: PatchConfig(
            pick={"kind", "id", "name", "bark_volume", "trained"},
            required={"kind", "id"},
        ),
    },
)


engine = create_engine(
    "sqlite:///./examples/cat_dog_patch.db",
    echo=True,
    connect_args={"check_same_thread": False},
)


def seed_database() -> None:
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        existing = session.exec(select(Household)).first()
        if existing is not None:
            return

        household = Household(
            owner_name="Monique",
            address="1 Example Street",
            cats=[
                CatProfile(name="Mimi", lives=9, indoor_only=True),
                CatProfile(name="Kiki", lives=8, indoor_only=False),
            ],
            dogs=[
                DogProfile(name="Scout", bark_volume=4, trained=True),
            ],
            toys=[
                Toy(name="Feather wand", favourite=True),
                Toy(name="Tennis ball", favourite=False),
            ],
        )

        session.add(household)
        session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_database()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/households/{household_id}", response_model=Household)
def get_household(household_id: int) -> Household:
    with Session(engine) as session:
        household = session.get(Household, household_id)
        if household is None:
            raise HTTPException(status_code=404, detail="Household not found")
        return household


@app.patch("/households/{household_id}", response_model=Household)
def patch_household(
    household_id: int,
    request: HouseholdPatchRequest,
) -> Household:
    with Session(engine) as session:
        household = session.get(Household, household_id)
        if household is None:
            raise HTTPException(status_code=404, detail="Household not found")

        patch_data = request.model_dump(exclude_unset=True)

        household_patch = patch_data.get("household")
        if household_patch is not None:
            if household_patch["id"] != household_id:
                raise HTTPException(status_code=400, detail="Household id mismatch")

            for field_name in ("owner_name", "address"):
                if field_name in household_patch:
                    setattr(household, field_name, household_patch[field_name])

            for cat_patch in household_patch.get("cats", []):
                cat = session.get(CatProfile, cat_patch["id"])
                if cat is None or cat.household_id != household_id:
                    raise HTTPException(status_code=404, detail="Cat not found")
                for field_name in ("name", "lives", "indoor_only"):
                    if field_name in cat_patch:
                        setattr(cat, field_name, cat_patch[field_name])

            for dog_patch in household_patch.get("dogs", []):
                dog = session.get(DogProfile, dog_patch["id"])
                if dog is None or dog.household_id != household_id:
                    raise HTTPException(status_code=404, detail="Dog not found")
                for field_name in ("name", "bark_volume", "trained"):
                    if field_name in dog_patch:
                        setattr(dog, field_name, dog_patch[field_name])

            for toy_patch in household_patch.get("toys", []):
                toy = session.get(Toy, toy_patch["id"])
                if toy is None or toy.household_id != household_id:
                    raise HTTPException(status_code=404, detail="Toy not found")
                for field_name in ("name", "favourite"):
                    if field_name in toy_patch:
                        setattr(toy, field_name, toy_patch[field_name])

        session.add(household)
        session.commit()
        session.refresh(household)
        return household


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "examples.fastapi_sqlmodel_cat_dog_patch:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # IMPORTANT: keep False for debugging/breakpoints
        log_level="debug",
    )
