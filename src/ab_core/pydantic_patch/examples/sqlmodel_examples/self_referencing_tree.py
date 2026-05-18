"""Self-referencing SQLModel tree patch example."""

import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends as FDepends
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session

from ab_core.database.databases import Database
from ab_core.database.session_context import db_session_sync
from ab_core.dependency import Depends, inject
from ab_core.pydantic_patch.examples.sqlmodel_examples.models import QuoteLineItem
from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar
from ab_core.pydantic_patch.patch import Patch, PatchConfig

os.environ.setdefault("DATABASE_TYPE", "SQL_ALCHEMY")
os.environ.setdefault("DATABASE_SQL_ALCHEMY_URL", "sqlite:///./self_referencing_tree.db")

ENTITY_ID = 1


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


def seed(db: Database) -> None:
    """Create demo records if they do not already exist."""
    db.sync_upgrade_db()

    with db.sync_session() as session:
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


@asynccontextmanager
@inject
async def lifespan(
    _app: FastAPI,
    db: Annotated[Database, Depends(Database, persist=True)],
):
    """Run startup seed for the example app lifecycle."""
    seed(db)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/line-items/{line_item_id}", response_model=QuoteLineItemResponse)
def get_line_item(
    line_item_id: int,
    db_session: Annotated[Session, FDepends(db_session_sync)],
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
    db_session: Annotated[Session, FDepends(db_session_sync)],
) -> QuoteLineItem:
    """Patch a self-referencing line item tree."""
    line_item = db_session.get(QuoteLineItem, line_item_id)

    if line_item is None:
        raise HTTPException(status_code=404, detail="Line item not found")

    recursive_patch_orm_scalar(line_item, patch)

    db_session.add(line_item)
    db_session.flush()

    return line_item


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
