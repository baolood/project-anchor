from app.core.domain_command_types import DOMAIN_COMMAND_TYPES


def is_valid_domain_command_type(command_type: str) -> bool:
    return command_type in DOMAIN_COMMAND_TYPES
