from app.core.domain_command_checks import is_valid_domain_command_type
from app.core.domain_command_missing_required_fields import (
    get_missing_required_fields_for_domain_command,
)
from app.core.domain_command_unexpected_fields import (
    get_unexpected_fields_for_domain_command,
)


def validate_domain_command_payload(command_type: str, payload: dict) -> dict:
    safe_payload = payload if isinstance(payload, dict) else {}
    return {
        "command_type": command_type,
        "is_valid_command_type": is_valid_domain_command_type(command_type),
        "missing_required_fields": get_missing_required_fields_for_domain_command(
            command_type, safe_payload
        ),
        "unexpected_fields": get_unexpected_fields_for_domain_command(
            command_type, safe_payload
        ),
    }
