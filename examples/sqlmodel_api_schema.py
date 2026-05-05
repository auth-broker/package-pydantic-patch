import os
from contextlib import asynccontextmanager
from typing import Annotated, Mapping

from fastapi import Depends as FDepends
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session
from sqlmodel import Field, Relationship, SQLModel

from ab_core.database.databases import Database
from ab_core.database.session_context import db_session_sync
from ab_core.pydantic_patch.patch import Patch, PatchConfig
from ab_core.dependency import Depends, inject

# =========================
# ENV CONFIG (like pytest)
# =========================

os.environ.setdefault("DATABASE_TYPE", "SQL_ALCHEMY")
os.environ.setdefault("DATABASE_SQL_ALCHEMY_URL", "sqlite:///./example.db")
ENTITY_ID = 0

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
    pick={"owner_name", "cats", "dogs"},
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
        if session.get(Household, ENTITY_ID):
            return

        household = Household(
            id=ENTITY_ID,
            owner_name="Monique",
            cats=[Cat(id=10, name="Mimi", lives=9)],
            dogs=[Dog(id=20, name="Scout", bark_volume=5)],
        )

        session.add(household)
        session.commit()




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
def apply_scalar_patch(instance: SQLModel, data: Mapping[str, object]) -> None:
    for field_name, value in data.items():
        if field_name == "id":
            continue

        setattr(instance, field_name, value)


def apply_child_list_patch(
    *,
    db_session: Session,
    model: type[SQLModel],
    data: list[Mapping[str, object]],
) -> None:
    for item_data in data:
        child_id = item_data["id"]
        child = db_session.get(model, child_id)

        if child is None:
            raise HTTPException(
                status_code=404,
                detail=f"{model.__name__} not found",
            )

        apply_scalar_patch(child, item_data)


@app.patch("/households", response_model=Household)
def patch_household(
    patch: HouseholdPatch,
    db_session: Annotated[Session, FDepends(db_session_sync)],
):
    data = patch.model_dump(exclude_unset=True)

    household = db_session.get(Household, ENTITY_ID)
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")

    household_data = {
        key: value
        for key, value in data.items()
        if key not in {"cats", "dogs"}
    }
    apply_scalar_patch(household, household_data)

    if "cats" in data:
        apply_child_list_patch(
            db_session=db_session,
            model=Cat,
            data=data["cats"],
        )

    if "dogs" in data:
        apply_child_list_patch(
            db_session=db_session,
            model=Dog,
            data=data["dogs"],
        )

    return household


# =========================
# RUN
# =========================

if __name__ == "__main__":
    import uvicorn

    # http://localhost:8000/docs#/default/upsert_household_households_patch
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
