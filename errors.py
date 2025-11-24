class FixedWidthError(Exception):
    """Base error for the library."""

class InvalidFileStructure(FixedWidthError):
    """Header/Footer missing or line length incorrect."""

class ValidationError(FixedWidthError):
    """Data validation error."""

class FieldLockedError(FixedWidthError):
    """Attempt to modify a locked field."""