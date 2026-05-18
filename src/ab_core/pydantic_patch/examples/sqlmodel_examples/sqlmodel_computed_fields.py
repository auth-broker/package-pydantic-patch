"""SQLModel computed-field patch example."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

import ab_core.pydantic_patch.examples.sqlmodel_examples.models.user as user_module
from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar
from ab_core.pydantic_patch.patch import Patch

User = user_module.User
ENTITY_ID = 1

# =========================
# PATCH MODEL
# =========================

UserPatch = Patch[User](
    pick={
        "first_name",
        "full_name",
        "email_domain",
    },
    partial={
        "first_name",
    },
    required={
        "full_name",
    },
)

UserResponse = Patch[User](
    name="UserResponse",
    pick={
        "id",
        "first_name",
        "last_name",
        "email",
        "full_name",
        "email_domain",
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
    USERS.setdefault(
        ENTITY_ID,
        User(
            id=ENTITY_ID,
            first_name="Monique",
            last_name="Kuhn",
            email="monique@example.com",
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
    user = USERS.get(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.patch("/users/{user_id}", response_model=UserResponse)
def patch_user(
    user_id: int,
    patch: UserPatch,
) -> User:
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
