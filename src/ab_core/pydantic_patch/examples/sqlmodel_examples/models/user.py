"""SQLModel computed-field patch example."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import computed_field
from sqlmodel import Field, SQLModel

from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar
from ab_core.pydantic_patch.patch import Patch

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
        return f"{self.first_name} {self.last_name}"

    @computed_field
    @property
    def email_domain(self) -> str:
        return self.email.split("@")[-1]
