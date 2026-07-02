"""SQLModel hybrid-property patch example."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy.ext.hybrid import hybrid_property
from sqlmodel import Field, SQLModel

from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar
from ab_core.pydantic_patch.patch import Patch

ENTITY_ID = 1


# =========================
# MODELS
# =========================


class User(SQLModel, table=True):
    __tablename__ = "hybrid_property_example_user"

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
        """Return the SQL expression for the user's full name."""
        return cls.first_name + " " + cls.last_name

    @hybrid_property
    def is_adult(self) -> bool:
        """Return whether the user is an adult."""
        return self.age >= 18

    @is_adult.expression
    def is_adult(cls):
        """Return the SQL expression for adult users."""
        return cls.age >= 18


# =========================
# PATCH MODELS
# =========================


UserPatch = Patch[User](
    pick={
        "first_name",
        "last_name",
        "age",
        "full_name",
        "is_adult",
    },
    partial={
        "first_name",
        "last_name",
        "age",
    },
    required={
        "full_name",
        "is_adult",
    },
)

UserResponse = Patch[User](
    name="HybridPropertyUserResponse",
    pick={
        "id",
        "first_name",
        "last_name",
        "age",
        "full_name",
        "is_adult",
    },
    required={
        "id",
    },
)


# =========================
# STORE
# =========================


USERS: dict[int, User] = {}


def seed() -> None:
    """Create demo records if they do not already exist."""
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


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int) -> User:
    """Return a user by id."""
    user = USERS.get(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.patch("/users/{user_id}", response_model=UserResponse)
def patch_user(
    user_id: int,
    patch: UserPatch,
) -> User:
    """Apply a patch model to a user."""
    user = USERS.get(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    recursive_patch_orm_scalar(user, patch)

    return user


# =========================
# RUN
# =========================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
