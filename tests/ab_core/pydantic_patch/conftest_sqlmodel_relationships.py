from sqlmodel import Field, Relationship, SQLModel


class SQLModelRelationshipPet(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    age: int
    household_id: int | None = Field(default=None, foreign_key="sqlmodelrelationshiphousehold.id")


class SQLModelRelationshipToy(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    household_id: int | None = Field(default=None, foreign_key="sqlmodelrelationshiphousehold.id")


class SQLModelRelationshipHousehold(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_name: str

    pets: list[SQLModelRelationshipPet] = Relationship()
    toys: list[SQLModelRelationshipToy] = Relationship()
