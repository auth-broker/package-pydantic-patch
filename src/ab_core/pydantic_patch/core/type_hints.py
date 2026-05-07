from typing import get_type_hints

from pydantic import BaseModel

from .errors import ForwardReferencesNotSupported
from .forward_references import build_forward_ref_error_message, unresolved_annotation_names


def get_resolved_type_hints(model: type[BaseModel]) -> dict[str, object]:
    unresolved = unresolved_annotation_names(model)

    if unresolved:
        raise ForwardReferencesNotSupported(
            build_forward_ref_error_message(
                model=model,
                unresolved_fields=unresolved,
            )
        )

    try:
        return get_type_hints(model, include_extras=True)
    except NameError as exc:
        raise ForwardReferencesNotSupported(
            build_forward_ref_error_message(
                model=model,
                unresolved_fields=list(getattr(model, "__annotations__", {})),
            )
        ) from exc
