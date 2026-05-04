ALLOWED_STRATEGY_VERSIONS = {
    "v1",
    "v2026.04.02",
}


def is_allowed_version(version: str) -> bool:
    return version in ALLOWED_STRATEGY_VERSIONS
