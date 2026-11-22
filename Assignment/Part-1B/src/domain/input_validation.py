class InputValidationError(ValueError):
    pass


def validate_customer_message(message: object) -> str:
    if not isinstance(message, str):
        raise InputValidationError("Customer message must be a string.")
    if not message.strip():
        raise InputValidationError("Customer message must not be empty or whitespace-only.")
    return message
