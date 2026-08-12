"""Broken forward-reference SQLModel example app."""

import os
from collections.abc import Generator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends as FDepends
from fastapi import FastAPI, HTTPException
from sqlmodel import Session, SQLModel, create_engine

from pydantic_patch.examples.sqlmodel_examples.models import (
    Project,
    ProjectMilestone,
    ProjectTask,
    TaskComment,
)
from pydantic_patch.orm_patch import recursive_patch_orm_scalar
from pydantic_patch.patch import Patch, PatchConfig

os.environ.setdefault("DATABASE_TYPE", "SQL_ALCHEMY")
os.environ.setdefault("DATABASE_SQL_ALCHEMY_URL", "sqlite:///./project_forward_refs_broken.db")

ENTITY_ID = 1
engine = create_engine(os.environ["DATABASE_SQL_ALCHEMY_URL"])

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


def seed() -> None:
    """Create demo records if they do not already exist."""
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
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


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db_session: Annotated[Session, FDepends(get_db_session)],
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
    db_session: Annotated[Session, FDepends(get_db_session)],
) -> Project:
    """Apply a patch model to a project and persist changes."""
    project = db_session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    recursive_patch_orm_scalar(project, patch)

    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

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
