"""Descriptor that enables read-only class-level properties."""


class classproperty:
    """Wrap a function so it can be accessed like a class property."""

    def __init__(self, func):
        """Store the wrapped accessor function."""
        self.func = func

    def __get__(self, obj, owner):
        """Resolve the property value from the owning class."""
        # owner is the class itself
        return self.func(owner)
