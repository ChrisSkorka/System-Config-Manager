# pyright: strict

from typing import TypeIs


class ValidationError(Exception):
    """
    Raised when user supplied input fails validation.

    These are expected, actionable mistakes - a missing file, a malformed
    config - not programming errors. The cli entry point presents them as a
    plain message rather than a traceback.

    Programming errors keep using `assert` and keep producing tracebacks.
    """


def validate(condition: bool, message: str) -> None:
    """
    Raise a ValidationError with the message unless the condition holds.

    Args:
        condition (bool): The condition that must hold.
        message (str): The message shown to the user when it does not.
    Returns:
        None
    """

    if not condition:
        raise ValidationError(message)


def validate_type[T](value: object, target_type: type[T], message: str) -> TypeIs[T]:
    """
    Raise a ValidationError unless the value is an instance of the target type.

    Returns a TypeIs so that `assert require_type(value, str, '...')` narrows
    the value for the type checker. A bare call does not narrow, so call sites
    that rely on narrowing must use the assert form.

    Args:
        value (object): The value to check.
        target_type (type[T]): The type the value must be an instance of.
        message (str): The message shown to the user when it is not.
    Returns:
        TypeIs[T]: Always True; the failure path raises.
    """

    if not isinstance(value, target_type):
        raise ValidationError(message)

    return True
