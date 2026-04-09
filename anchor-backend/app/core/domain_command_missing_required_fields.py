from app.core.domain_command_required_field_checks import (
    get_required_fields_for_domain_command,
)


def get_missing_required_fields_for_domain_command(
    command_type: str, payload: dict
) -> tuple[str, ...]:
    required_fields = get_required_fields_for_domain_command(command_type)
    return tuple(field for field in required_fields if field not in payload)
