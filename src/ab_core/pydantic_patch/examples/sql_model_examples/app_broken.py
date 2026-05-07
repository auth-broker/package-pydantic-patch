import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends as FDepends
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session

from ab_core.database.databases import Database
from ab_core.database.session_context import db_session_sync
from ab_core.dependency import Depends, inject
from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar

from ab_core.pydantic_patch.examples.sql_model_examples.models import (
    Project,
    ProjectMilestone,
    ProjectTask,
    TaskComment,
)
from ab_core.pydantic_patch.examples.sql_model_examples.schemas import ProjectPatch

os.environ.setdefault("DATABASE_TYPE", "SQL_ALCHEMY")
os.environ.setdefault("DATABASE_SQL_ALCHEMY_URL", "sqlite:///./project_forward_refs_broken.db")

ENTITY_ID = 1


def seed(db: Database) -> None:
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
    seed(db)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/projects/{project_id}", response_model=Project)
def get_project(
    project_id: int,
    db_session: Annotated[Session, FDepends(db_session_sync)],
) -> Project:
    project = db_session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@app.patch("/projects/{project_id}", response_model=Project)
def patch_project(
    project_id: int,
    patch: ProjectPatch,
    db_session: Annotated[Session, FDepends(db_session_sync)],
) -> Project:
    project = db_session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    recursive_patch_orm_scalar(project, patch)

    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    return project


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "examples.project_forward_refs.app_broken:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )