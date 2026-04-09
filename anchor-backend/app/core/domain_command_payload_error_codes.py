from app.core.domain_command_payload_validation import validate_domain_command_payload


def get_domain_command_payload_error_codes(
    command_type: str, payload: dict
) -> tuple[str, ...]:
    result = validate_domain_command_payload(command_type, payload)
    errors = []
    if result["is_valid_command_type"] is not True:
        errors.append("INVALID_COMMAND_TYPE")
    if result["missing_required_fields"] != ():
        errors.append("MISSING_REQUIRED_FIELDS")
    if result["unexpected_fields"] != ():
        errors.append("UNEXPECTED_FIELDS")
    return tuple(errors)
