"""Task comment SQLModel for the nested forward-reference example."""

from sqlmodel import Field, Relationship, SQLModel


class TaskComment(SQLModel, table=True):
    """Comment child entity for a task."""

    __tablename__ = "task_comment"

    id: int | None = Field(default=None, primary_key=True)
    body: str
    task_id: int | None = Field(default=None, foreign_key="project_task.id")

    task: "ProjectTask" = Relationship(back_populates="comments")
