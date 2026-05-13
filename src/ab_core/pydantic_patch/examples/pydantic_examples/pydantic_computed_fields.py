"""Pydantic computed-field patch example."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, computed_field

from ab_core.pydantic_patch.orm_patch import recursive_patch_scalar
from ab_core.pydantic_patch.patch import Patch

ENTITY_ID = 1


# =========================
# MODELS
# =========================


class User(BaseModel):
    id: int
    first_name: str
    last_name: str
    age: int

    @computed_field
    @property
    def full_name(self) -> str:
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}"

    @computed_field
    @property
    def is_adult(self) -> bool:
        """Return whether the user is an adult."""
        return self.age >= 18


# =========================
# PATCH MODEL
# =========================

UserPatch = Patch[User](
    pick={
        "first_name",
        "last_name",
        "full_name",
    },
    partial={
        "first_name",
        "last_name",
    },
    required={
        "full_name",
    },
)


# =========================
# STORE
# =========================

USERS: dict[int, User] = {}


def seed() -> None:
    USERS.setdefault(
        ENTITY_ID,
        User(
            id=ENTITY_ID,
            first_name="Monique",
            last_name="Kuhn",
            age=28,
        ),
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed()
    yield


app = FastAPI(lifespan=lifespan)


# =========================
# API
# =========================


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int) -> User:
    user = USERS.get(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.patch("/users/{user_id}", response_model=User)
def patch_user(
    user_id: int,
    patch: UserPatch,
) -> User:
    user = USERS.get(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    recursive_patch_scalar(user, patch)

    return user


# =========================
# RUN
# =========================


def get_module_path(file_path: str) -> str:
    parts = Path(file_path).resolve().with_suffix("").relative_to(Path.cwd()).parts

    if parts[0] == "src":
        parts = parts[1:]

    return ".".join(parts)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        f"{get_module_path(__file__)}:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
