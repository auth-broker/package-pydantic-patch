"""Project milestone SQLModel for the nested forward-reference example."""

from sqlmodel import Field, Relationship, SQLModel


class ProjectMilestone(SQLModel, table=True):
    """Milestone child entity for a project."""

    __tablename__ = "project_milestone"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    project_id: int | None = Field(default=None, foreign_key="project.id")

    project: "Project" = Relationship(back_populates="milestones")
    tasks: list["ProjectTask"] = Relationship(back_populates="milestone")
