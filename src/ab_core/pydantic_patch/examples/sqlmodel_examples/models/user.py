"""SQLModel computed-field patch example."""

from pydantic import computed_field
from sqlmodel import Field, SQLModel

ENTITY_ID = 1


# =========================
# MODELS
# =========================


class User(SQLModel, table=True):
    __tablename__ = "computed_field_user"

    id: int | None = Field(default=None, primary_key=True)

    first_name: str
    last_name: str
    email: str

    @computed_field
    @property
    def full_name(self) -> str:
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}"

    @computed_field
    @property
    def email_domain(self) -> str:
        """Return the email domain portion."""
        return self.email.split("@")[-1]
