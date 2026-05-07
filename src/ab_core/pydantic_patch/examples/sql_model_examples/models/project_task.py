"""Project task SQLModel for the nested forward-reference example."""

from sqlmodel import Field, Relationship, SQLModel


class ProjectTask(SQLModel, table=True):
    """Task child entity for a milestone."""

    __tablename__ = "project_task"

    id: int | None = Field(default=None, primary_key=True)
    title: str
    milestone_id: int | None = Field(default=None, foreign_key="project_milestone.id")

    milestone: "ProjectMilestone" = Relationship(back_populates="tasks")
    comments: list["TaskComment"] = Relationship(back_populates="task")
