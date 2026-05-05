<div align="center">

# PATCH for Pydantic

Python Pydantic support of TypeScript-style utility types, including Partial, Required, Pick, and Omit. Useful for PATCH endpoints driven from BaseModel / SQLModel classes.

![Python](https://img.shields.io/badge/Python-3.12-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![UV](https://img.shields.io/badge/UV-Fast-6E40C9?style=for-the-badge)
![Hatchling](https://img.shields.io/badge/Hatchling-PEP517-6E40C9?style=for-the-badge)
![Ruff](https://img.shields.io/badge/Ruff-Lint-000000?style=for-the-badge)
![Pre-commit](https://img.shields.io/badge/Pre--commit-Hooks-000000?style=for-the-badge)
![Pytest](https://img.shields.io/badge/Pytest-Unit%2BAsync-08979C?style=for-the-badge)
![Coverage](https://img.shields.io/badge/Cov-Reports-08979C?style=for-the-badge)
![GitHub Actions](https://img.shields.io/badge/Actions-CI%2FCD-F7B500?style=for-the-badge&logo=github-actions)
![PyPI](https://img.shields.io/badge/PyPI-Publish-6E40C9?style=for-the-badge)
![Makefile](https://img.shields.io/badge/Makefile-Scripts-F7B500?style=for-the-badge)

🦜🕸️

[![CI](https://github.com/auth-broker/package-pydantic-patch/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/auth-broker/package-pydantic-patch/actions/workflows/ci.yaml)

</div>

______________________________________________________________________

## Table of Contents

<!-- toc -->

- [Introduction](#introduction)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Formatting and linting](#formatting-and-linting)
- [CICD](#cicd)

<!-- tocstop -->

______________________________________________________________________

## Introduction

Python is missing a key feature of modern day dynamic programming languages.

Namely, TypeScript supports these utility types: https://www.typescriptlang.org/docs/handbook/utility-types.html

* Partial<T>: Makes all properties in type T optional. Useful for update forms or search filters where you only provide a subset of fields. [5, 6, 7] 
* Required<T>: The opposite of Partial; it makes all properties in type T mandatory, even if they were originally optional. [7, 8, 9] 
* Pick<T, K>: Creates a new type by selecting a specific set of keys K from type T. Use this when you only need a small, focused subset of a larger object. [10, 11, 12] 
* Omit<T, K>: The opposite of Pick; it creates a new type by removing specific keys K from type T. Use this when you want most of an object but need to strip out sensitive data (like passwords) or internal IDs. [1, 7, 13, 14, 15] 

Because of this missing support in python, developers are often encouraged to duplicate their models & field definitions between their API and ORM
definitions, which becomes a really tedious and feels like it involves double handling.

Especially for PATCH endpoints when we want to update something, should we really need to manually redefine the schema? Especially
with larger nested JSON schemas, and even with Discriminated Unions, it becomes a really cumbersome and limited chore a developer
must do to separate the API schema from their application models, when there is almost always an overlap in structure and field definitions.

This is the motivation behind building "PATCH for Pydantic".

Ultimately, with the really mature pydantic library, it actually makes building a package like this not too complicated.

______________________________________________________________________

## Quick Start

Since this is just a package, and not a service, there is no real "run" action.
But you can run the tests immediately.

Here are a list of available commands via make.

### Bare Metal (i.e. your machine)

1. `make install` - install the required dependencies.
2. `make test` - runs the tests.

### Docker

1. `make build-docker` - build the docker image.
2. `make run-docker` - run the docker compose services.
3. `make test-docker` - run the tests in docker.
4. `make clean-docker` - remove all docker containers etc.

______________________________________________________________________

## Installation

### For Dev work on the repo

Install `uv`, (_if you haven't already_)
https://docs.astral.sh/uv/getting-started/installation/#installation-methods

```shell
brew install uv
```

Initialise pre-commit (validates ruff on commit.)

```shell
uv run pre-commit install
```

Install dependencies (including dev dependencies)

```shell
uv sync
```

If you are adding a new dev dependency, please run:

```shell
uv add --dev {your-new-package}
```

### Namespaces

Packages all share the same namespace `ab_core`. To import this package into
your project:

```python
from ab_core.template import placeholder_func
```

We encourage you to make your package available to all of ab via this
`ab_core` namespace. The goal is to streamline development, POCs and overall
collaboration.

______________________________________________________________________

## Usage

### Adding the dependency to your project

The library is available on PyPI. You can install it using the following
command:

**Using pip**:

```shell
pip install ab-pydantic-patch
```

**Using UV**

Note: there is currently no nice way like poetry, hence we still needd to
provide the full url. https://github.com/astral-sh/uv/issues/10140

Add the dependency

```shell
uv add ab-pydantic-patch
```

**Using poetry**:

Then run the following command to install the package:

```shell
poetry add ab-pydantic-patch
```

## How Tos

---

### Pick

Select a subset of fields.

#### Python

**Before**

```python
class User(BaseModel):
    id: int
    name: str
    email: str
```

**Transform**

```python
UserPick = Pick[User](fields={"id", "name"})
```

**After (conceptual)**

```python
class UserPick(BaseModel):
    id: int
    name: str
```

---

#### TypeScript equivalent

```ts
type User = {
  id: number
  name: string
  email: string
}

type UserPick = Pick<User, "id" | "name">
```

---

### Omit

Remove specific fields.

#### Python

**Before**

```python
class User(BaseModel):
    id: int
    name: str
    email: str
```

**Transform**

```python
UserOmit = Omit[User](fields={"email"})
```

**After (conceptual)**

```python
class UserOmit(BaseModel):
    id: int
    name: str
```

---

#### TypeScript equivalent

```ts
type User = {
  id: number
  name: string
  email: string
}

type UserOmit = Omit<User, "email">
```

---

### Partial

Make fields optional.

#### Python

**Before**

```python
class User(BaseModel):
    id: int
    name: str
```

**Transform**

```python
UserPartial = Partial[User](fields={"name"})
```

**After (conceptual)**

```python
class UserPartial(BaseModel):
    id: int
    name: str | None = None
```

---

#### TypeScript equivalent

```ts
type User = {
  id: number
  name: string
}

type UserPartial = Partial<Pick<User, "name">> & Pick<User, "id">
```

---

### Required

Force fields to be required.

#### Python

**Before**

```python
class User(BaseModel):
    id: int | None = None
    name: str | None = None
```

**Transform**

```python
UserRequired = Required[User](fields={"id"})
```

**After (conceptual)**

```python
class UserRequired(BaseModel):
    id: int
    name: str | None = None
```

---

#### TypeScript equivalent

```ts
type User = {
  id?: number
  name?: string
}

type UserRequired = Required<Pick<User, "id">> & Omit<User, "id">
```

---

### Patch (combine operations)

#### Python

**Before**

```python
class User(BaseModel):
    id: int
    name: str
    email: str
```

**Transform**

```python
UserPatch = Patch[User](
    pick={"id", "name"},
    partial={"name"},
    required={"id"},
)
```

**After (conceptual)**

```python
class UserPatch(BaseModel):
    id: int
    name: str | None = None
```

---

### `set()` vs `None`

```python
Patch[User](partial=None)
```

→ all fields optional

```python
class UserPatch(BaseModel):
    id: int | None = None
    name: str | None = None
    email: str | None = None
```

---

```python
Patch[User](partial=set())
```

→ no fields optional

```python
class UserPatch(BaseModel):
    id: int
    name: str
    email: str
```

---

### Parent / Child (nested models)

#### Python

**Before**

```python
class Pet(BaseModel):
    id: int
    name: str
    type: str


class Household(BaseModel):
    id: int
    owner_name: str
    pets: list[Pet]
```

---

**Transform**

```python
HouseholdPatch = Patch[Household](
    pick={"id", "pets"},
    required={"id"},
    child_models={
        Pet: PatchConfig(
            pick={"id", "name"},
            partial={"name"},
            required={"id"},
        )
    }
)
```

---

**After (conceptual)**

```python
class PetPatch(BaseModel):
    id: int
    name: str | None = None


class HouseholdPatch(BaseModel):
    id: int
    pets: list[PetPatch] | None = None
```

---

### Discriminated Union

#### Python

**Before**

```python
from typing import Annotated, Union, Literal
from pydantic import Field


class Cat(BaseModel):
    kind: Literal["cat"]
    id: int
    name: str


class Dog(BaseModel):
    kind: Literal["dog"]
    id: int
    name: str


Pet = Annotated[Union[Cat, Dog], Field(discriminator="kind")]


class Owner(BaseModel):
    pet: Pet
```

---

**Transform**

```python
OwnerPatch = Patch[Owner](
    pick={"pet"},
    child_models={
        Cat: PatchConfig(
            pick={"kind", "id", "name"},
            partial={"name"},
            required={"id"},
        ),
        Dog: PatchConfig(
            pick={"kind", "id", "name"},
            partial={"name"},
            required={"id"},
        ),
    }
)
```

---

**After (conceptual)**

```python
class CatPatch(BaseModel):
    kind: Literal["cat"]
    id: int
    name: str | None = None


class DogPatch(BaseModel):
    kind: Literal["dog"]
    id: int
    name: str | None = None


PetPatch = Annotated[
    CatPatch | DogPatch,
    Field(discriminator="kind")
]


class OwnerPatch(BaseModel):
    pet: PetPatch | None = None
```

---

### SQLModel Relationships

#### Python

**Before**

```python
from sqlmodel import SQLModel, Field, Relationship


class Pet(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    household_id: int | None = Field(default=None, foreign_key="household.id")


class Household(SQLModel, table=True):
    id: int = Field(primary_key=True)
    pets: list[Pet] = Relationship(back_populates="household")
```

---

**Transform**

```python
HouseholdPatch = Patch[Household](
    pick={"id", "pets"},
    required={"id"},
    child_models={
        Pet: PatchConfig(
            pick={"id", "name"},
            required={"id"},
        )
    }
)
```

---

**After (conceptual)**

```python
class PetPatch(BaseModel):
    id: int
    name: str | None = None


class HouseholdPatch(BaseModel):
    id: int
    pets: list[PetPatch] | None = None
```

---

## Additional Notes

### Caching

* Same model + same config → same generated class
* Nested models reuse generated types
* Improves performance and consistency

---

### Discriminated unions

* Discriminator field is always required
* Cannot be omitted or made optional
* Each variant is transformed independently

---

### Operation order

Applied in this order:

1. pick / omit
2. partial
3. required (final override)

---

### Validation / Errors

* Unknown fields → error
* Required field removed by pick/omit → error
* Discriminator misconfiguration → error
* Invalid nested configs → error

---

### Supported types

* `BaseModel`
* `list[...]`
* `dict[...]`
* `Union` / `Annotated`
* SQLModel (including relationships)

______________________________________________________________________

## Formatting and linting

We use Ruff as the formatter and linter. The pre-commit has hooks which runs
checking and applies linting automatically. The CI validates the linting,
ensuring main is always looking clean.

You can manually use these commands too:

1. `make lint` - check for linting issues.
2. `make format` - fix linting issues.

______________________________________________________________________

## CICD

### Publishing to PyPI

We publish to PyPI using Github releases. Steps are as follows:

1. Manually update the version in `pyproject.toml` file using a PR and merge to
   main. Use `uv version --bump {patch/minor/major}` to update the version.
2. Create a new release in Github with the tag name as the version number. This
   will trigger the `publish` workflow. In the Release window, type in the
   version number and it will prompt to create a new tag.
3. Verify the release in
   [PyPI](https://pypi.org/project/ab-pydantic-patch/)
