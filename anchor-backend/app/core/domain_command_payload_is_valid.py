from app.core.domain_command_payload_validation import validate_domain_command_payload


def is_domain_command_payload_valid(command_type: str, payload: dict) -> bool:
    result = validate_domain_command_payload(command_type, payload)
    return (
        result["is_valid_command_type"] is True
        and result["missing_required_fields"] == ()
        and result["unexpected_fields"] == ()
    )
