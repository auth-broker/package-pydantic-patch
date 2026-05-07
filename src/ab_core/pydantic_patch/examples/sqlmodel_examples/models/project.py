"""Project SQLModel for the nested forward-reference example."""

from sqlmodel import Field, Relationship, SQLModel


class Project(SQLModel, table=True):
    """Top-level project aggregate."""

    __tablename__ = "project"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    milestones: list["ProjectMilestone"] = Relationship(back_populates="project")
