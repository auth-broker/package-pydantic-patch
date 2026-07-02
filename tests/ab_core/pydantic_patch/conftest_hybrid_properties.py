from sqlalchemy.ext.hybrid import hybrid_property
from sqlmodel import Field, SQLModel


class HybridPropertyUser(SQLModel, table=True):
    __tablename__ = "hybrid_property_user"

    id: int | None = Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    age: int

    @hybrid_property
    def full_name(self) -> str:
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}"

    @full_name.expression
    def full_name(cls):
        """Return SQL expression for full name."""
        return cls.first_name + " " + cls.last_name

    @hybrid_property
    def is_adult(self) -> bool:
        """Return whether the user is an adult."""
        return self.age >= 18

    @is_adult.expression
    def is_adult(cls):
        """Return SQL expression for adult status."""
        return cls.age >= 18


class HybridPropertyForwardRefModel(SQLModel):
    @hybrid_property
    def manager(self) -> "HybridMissingManager":
        """Return the unresolved manager reference."""
        raise NotImplementedError
