"""Errors raised by pydantic_patch."""

from __future__ import annotations


class PydanticPatchError(Exception):
    """Base exception for pydantic_patch errors."""


class InvalidPatchFieldError(PydanticPatchError):
    """Raised when a configured field does not exist on the target model."""


class InvalidDiscriminatorError(PydanticPatchError):
    """Raised when a discriminated-union transformation would break discrimination."""


class UnsupportedAnnotationError(PydanticPatchError):
    """Raised when an annotation cannot be transformed safely."""


class ConflictingPatchConfigError(PydanticPatchError):
    """Raised when operation configuration conflicts with the generated payload."""
