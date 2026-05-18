"""Broken forward-reference SQLModel example app."""

import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends as FDepends
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session

from ab_core.database.databases import Database
from ab_core.database.session_context import db_session_sync
from ab_core.dependency import Depends, inject
from ab_core.pydantic_patch.examples.sqlmodel_examples.models import (
    Project,
    ProjectMilestone,
    ProjectTask,
    TaskComment,
)
from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar
from ab_core.pydantic_patch.patch import Patch, PatchConfig

os.environ.setdefault("DATABASE_TYPE", "SQL_ALCHEMY")
os.environ.setdefault("DATABASE_SQL_ALCHEMY_URL", "sqlite:///./project_forward_refs_broken.db")

ENTITY_ID = 1

ProjectPatch = Patch[Project](
    pick={"name", "milestones"},
    child_models={
        ProjectMilestone: PatchConfig(
            pick={"id", "name", "tasks"},
        ),
        ProjectTask: PatchConfig(
            pick={"id", "title", "comments"},
        ),
        TaskComment: PatchConfig(
            pick={"id", "body"},
        ),
    },
)

ProjectResponse = Patch[Project](
    name="ProjectResponse",
    pick={"id", "name", "milestones"},
    required={"id"},
    child_models={
        ProjectMilestone: PatchConfig(
            pick={"id", "name", "tasks"},
            required={"id"},
        ),
        ProjectTask: PatchConfig(
            pick={"id", "title", "comments"},
            required={"id"},
        ),
        TaskComment: PatchConfig(
            pick={"id", "body"},
            required={"id"},
        ),
    },
)


def seed(db: Database) -> None:
    """Create demo records if they do not already exist."""
    db.sync_upgrade_db()

    with db.sync_session() as session:
        if session.get(Project, ENTITY_ID):
            return

        project = Project(
            id=ENTITY_ID,
            name="Website Refresh",
            milestones=[
                ProjectMilestone(
                    id=10,
                    name="Launch Prep",
                    tasks=[
                        ProjectTask(
                            id=100,
                            title="Update homepage",
                            comments=[
                                TaskComment(
                                    id=1000,
                                    body="Initial stakeholder note",
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        session.add(project)
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


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db_session: Annotated[Session, FDepends(db_session_sync)],
) -> Project:
    """Return a project by id."""
    project = db_session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@app.patch("/projects/{project_id}", response_model=ProjectResponse)
def patch_project(
    project_id: int,
    patch: ProjectPatch,
    db_session: Annotated[Session, FDepends(db_session_sync)],
) -> Project:
    """Apply a patch model to a project and persist changes."""
    project = db_session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    recursive_patch_orm_scalar(project, patch)

    db_session.add(project)

    return project


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
