from app.core.domain_command_allowed_field_checks import get_allowed_fields_for_domain_command


def get_unexpected_fields_for_domain_command(
    command_type: str, payload: dict
) -> tuple[str, ...]:
    allowed_fields = get_allowed_fields_for_domain_command(command_type)
    return tuple(field for field in payload if field not in allowed_fields)
