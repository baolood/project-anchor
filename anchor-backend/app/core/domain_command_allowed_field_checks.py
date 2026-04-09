from app.core.domain_command_allowed_fields import DOMAIN_COMMAND_ALLOWED_FIELDS


def get_allowed_fields_for_domain_command(command_type: str) -> tuple[str, ...]:
    return DOMAIN_COMMAND_ALLOWED_FIELDS.get(command_type, ())
