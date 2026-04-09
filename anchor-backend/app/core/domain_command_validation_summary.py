from app.core.domain_command_payload_error_codes import (
    get_domain_command_payload_error_codes,
)
from app.core.domain_command_payload_is_valid import is_domain_command_payload_valid
from app.core.domain_command_payload_validation import validate_domain_command_payload


def summarize_domain_command_validation(command_type: str, payload: dict) -> dict:
    validation = validate_domain_command_payload(command_type, payload)
    return {
        "command_type": command_type,
        "is_valid": is_domain_command_payload_valid(command_type, payload),
        "error_codes": get_domain_command_payload_error_codes(command_type, payload),
        "validation": validation,
    }
