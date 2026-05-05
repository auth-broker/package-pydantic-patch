import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends as FDepends
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session
from sqlmodel import Field, Relationship, SQLModel

from ab_core.database.databases import Database
from ab_core.database.session_context import db_session_sync
from ab_core.pydantic_patch.patch import Patch, PatchConfig

# =========================
# ENV CONFIG (like pytest)
# =========================

os.environ.setdefault("DATABASE_TYPE", "SQL_ALCHEMY")
os.environ.setdefault("DATABASE_SQL_ALCHEMY_URL", "sqlite:///./example.db")


# =========================
# MODELS
# =========================


class Cat(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    lives: int
    household_id: int | None = Field(default=None, foreign_key="household.id")


class Dog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    bark_volume: int
    household_id: int | None = Field(default=None, foreign_key="household.id")


class Household(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_name: str

    cats: list[Cat] = Relationship()
    dogs: list[Dog] = Relationship()


# =========================
# PATCH MODEL
# =========================

HouseholdPatch = Patch[Household](
    pick={"id", "owner_name", "cats", "dogs"},
    required={"id"},
    child_models={
        Cat: PatchConfig(
            pick={"id", "name"},  # cannot edit lives
            required={"id"},
        ),
        Dog: PatchConfig(
            pick={"id", "name"},  # cannot edit bark_volume
            required={"id"},
        ),
    },
)


# =========================
# STARTUP / SEED
# =========================


def seed(db: Database):
    db.sync_upgrade_db()

    with db.sync_session() as session:
        if session.get(Household, 1):
            return

        household = Household(
            id=1,
            owner_name="Monique",
            cats=[Cat(id=10, name="Mimi", lives=9)],
            dogs=[Dog(id=20, name="Scout", bark_volume=5)],
        )

        session.add(household)
        session.commit()


from ab_core.dependency import Depends, inject


@asynccontextmanager
@inject
async def lifespan(
    app: FastAPI,
    db: Annotated[Database, Depends(Database, persist=True)],  # cold start load db into cache
):
    seed(db)
    yield


app = FastAPI(lifespan=lifespan)


# =========================
# API
# =========================
@app.patch("/households", response_model=Household)
def upsert_household(
    patch: HouseholdPatch,
    db_session: Annotated[Session, FDepends(db_session_sync)],
):
    data = patch.model_dump(exclude_unset=True)

    household = db_session.get(Household, data["id"])

    if household is None:
        household = Household(**data)
        db_session.add(household)
    else:
        if "owner_name" in data:
            household.owner_name = data["owner_name"]

        for cat_patch in data.get("cats", []):
            cat = db_session.get(Cat, cat_patch["id"])
            if cat is None:
                raise HTTPException(404, "Cat not found")

            if "name" in cat_patch:
                cat.name = cat_patch["name"]

        for dog_patch in data.get("dogs", []):
            dog = db_session.get(Dog, dog_patch["id"])
            if dog is None:
                raise HTTPException(404, "Dog not found")

            if "name" in dog_patch:
                dog.name = dog_patch["name"]

    db_session.commit()
    db_session.refresh(household)
    return household


# =========================
# RUN
# =========================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
