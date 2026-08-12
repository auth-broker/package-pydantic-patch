"""Self-referencing SQLModel tree patch example."""

import os
from collections.abc import Generator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends as FDepends
from fastapi import FastAPI, HTTPException
from sqlmodel import Session, SQLModel, create_engine

from pydantic_patch.examples.sqlmodel_examples.models import QuoteLineItem
from pydantic_patch.orm_patch import recursive_patch_orm_scalar
from pydantic_patch.patch import Patch, PatchConfig

os.environ.setdefault("DATABASE_TYPE", "SQL_ALCHEMY")
os.environ.setdefault("DATABASE_SQL_ALCHEMY_URL", "sqlite:///./self_referencing_tree.db")

ENTITY_ID = 1
engine = create_engine(os.environ["DATABASE_SQL_ALCHEMY_URL"])


QuoteLineItemPatch = Patch[QuoteLineItem](
    name="QuoteLineItemPatch",
    pick={
        "id",
        "line_item_name",
        "quoted_base_cost",
        "children",
    },
    partial={
        "id",
        "line_item_name",
        "quoted_base_cost",
        "children",
    },
    child_models={
        QuoteLineItem: PatchConfig(
            pick={
                "id",
                "line_item_name",
                "quoted_base_cost",
                "children",
            },
            partial={
                "id",
                "line_item_name",
                "quoted_base_cost",
                "children",
            },
        ),
    },
)

QuoteLineItemResponse = Patch[QuoteLineItem](
    name="QuoteLineItemResponse",
    pick={
        "id",
        "line_item_name",
        "quoted_base_cost",
        "children",
    },
    required={
        "id",
    },
    child_models={
        QuoteLineItem: PatchConfig(
            pick={
                "id",
                "line_item_name",
                "quoted_base_cost",
                "children",
            },
            required={
                "id",
            },
        ),
    },
)


def seed() -> None:
    """Create demo records if they do not already exist."""
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        if session.get(QuoteLineItem, ENTITY_ID):
            return

        quote_line_item = QuoteLineItem(
            id=ENTITY_ID,
            line_item_name="Fence",
            quoted_base_cost=1200.0,
            children=[
                QuoteLineItem(
                    id=10,
                    line_item_name="Panels",
                    quoted_base_cost=700.0,
                ),
                QuoteLineItem(
                    id=11,
                    line_item_name="Posts and rails",
                    quoted_base_cost=500.0,
                ),
            ],
        )

        session.add(quote_line_item)
        session.commit()


def get_db_session() -> Generator[Session]:
    """Yield a SQLModel session for FastAPI."""
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run startup seed for the example app lifecycle."""
    seed()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/line-items/{line_item_id}", response_model=QuoteLineItemResponse)
def get_line_item(
    line_item_id: int,
    db_session: Annotated[Session, FDepends(get_db_session)],
) -> QuoteLineItem:
    """Return a line item tree by id."""
    line_item = db_session.get(QuoteLineItem, line_item_id)

    if line_item is None:
        raise HTTPException(status_code=404, detail="Line item not found")

    return line_item


@app.patch("/line-items/{line_item_id}", response_model=QuoteLineItemResponse)
def patch_line_item(
    line_item_id: int,
    patch: QuoteLineItemPatch,
    db_session: Annotated[Session, FDepends(get_db_session)],
) -> QuoteLineItem:
    """Patch a self-referencing line item tree."""
    line_item = db_session.get(QuoteLineItem, line_item_id)

    if line_item is None:
        raise HTTPException(status_code=404, detail="Line item not found")

    recursive_patch_orm_scalar(line_item, patch)

    db_session.add(line_item)
    db_session.commit()
    db_session.refresh(line_item)

    return line_item


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
