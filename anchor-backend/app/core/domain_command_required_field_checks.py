from app.core.domain_command_required_fields import DOMAIN_COMMAND_REQUIRED_FIELDS


def get_required_fields_for_domain_command(command_type: str) -> tuple[str, ...]:
    return DOMAIN_COMMAND_REQUIRED_FIELDS.get(command_type, ())
