"""Founder-note unit classes for the host sidecar.

CORE_RUNTIME is the only class that gates overall PASS. EVALUATION,
AUXILIARY, and INTENTIONALLY_DISABLED are reported and do not.
"""

from __future__ import annotations

from typing import Mapping


CLASS_CORE_RUNTIME = "CORE_RUNTIME"
CLASS_EVALUATION = "EVALUATION"
CLASS_AUXILIARY = "AUXILIARY"
CLASS_INTENTIONALLY_DISABLED = "INTENTIONALLY_DISABLED"

GATING_CLASSES = (CLASS_CORE_RUNTIME,)
NON_GATING_CLASSES = (
    CLASS_EVALUATION,
    CLASS_AUXILIARY,
    CLASS_INTENTIONALLY_DISABLED,
)

HOST_SIDECAR_ENV = "ANCHOR_CONTROL_MCP_HOST_SIDECAR"
HOST_OBSERVE_LIMIT = 16

# Recommended ANCHOR_CONTROL_MCP_SERVICE_UNITS / TIMER_UNITS for the host sidecar.
# No timer in this repository is core runtime, so the timer list is empty.
RECOMMENDED_SERVICE_UNITS = ("docker.service",)
RECOMMENDED_TIMER_UNITS: tuple[str, ...] = ()
HOST_DEFAULT_SERVICES = RECOMMENDED_SERVICE_UNITS
HOST_DEFAULT_TIMERS = RECOMMENDED_TIMER_UNITS

# Fixed names the host sidecar may systemctl-show in addition to the operator
# allowlist. This is not a live Vultr dump and it is not a wildcard listing.
OBSERVE_SERVICES = (
    "docker.service",
    "project-anchor-post-production-monitoring.service",
    "nginx.service",
    "jev-forward-shadow-v2.service",
)
OBSERVE_TIMERS = ("project-anchor-post-production-monitoring.timer",)

# Exact units: founder notes plus units this repository installs or depends on.
EXACT_CLASSES: dict[str, tuple[str, str]] = {
    "docker.service": (
        CLASS_CORE_RUNTIME,
        "Host engine for the Docker backend, worker, Postgres, and Redis on 127.0.0.1",
    ),
    "project-anchor-post-production-monitoring.service": (
        CLASS_AUXILIARY,
        "Oneshot read-only monitoring refresh, not the trading runtime",
    ),
    "project-anchor-post-production-monitoring.timer": (
        CLASS_AUXILIARY,
        "Schedules the monitoring oneshot; observability does not gate PASS",
    ),
    "nginx.service": (
        CLASS_AUXILIARY,
        "Public edge for the example /mcp proxy; loopback runtime health does not require it",
    ),
    "jev-forward-shadow-v2.service": (
        CLASS_INTENTIONALLY_DISABLED,
        "Founder note: intentionally disabled and not required for health PASS",
    ),
}

# Name families from the founder note. Exact unit filenames for these families
# were not in the repository, so a matching name is classified without being
# invented as a concrete installed unit.
FAMILY_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "jev-forward-shadow-v2",
        CLASS_INTENTIONALLY_DISABLED,
        "Founder note: jev-forward-shadow-v2 is intentionally disabled",
    ),
    (
        "word-converter",
        CLASS_AUXILIARY,
        "Founder note: word-converter is a utility, not Anchor core runtime",
    ),
    (
        "word_converter",
        CLASS_AUXILIARY,
        "Founder note: word-converter is a utility, not Anchor core runtime",
    ),
    (
        "whisper",
        CLASS_AUXILIARY,
        "Founder note: whisper is not Anchor core runtime",
    ),
    (
        "commercial",
        CLASS_EVALUATION,
        "Founder note: commercial lane is evaluation, not Anchor core runtime",
    ),
    (
        "payment",
        CLASS_EVALUATION,
        "Founder note: payment lane is evaluation, not Anchor core runtime",
    ),
)


def host_sidecar_enabled(env: Mapping[str, str]) -> bool:
    return (env.get(HOST_SIDECAR_ENV) or "").strip() == "1"


def classify_unit(name: str) -> dict[str, object]:
    """Classify one unit name.

    An allowlisted name that matches neither the exact table nor a founder
    family stays CORE_RUNTIME so a new Anchor unit still gates PASS. The
    founder families never take that default.
    """
    exact = EXACT_CLASSES.get(name)
    if exact is not None:
        unit_class, reason = exact
    else:
        lowered = name.lower()
        unit_class = CLASS_CORE_RUNTIME
        reason = "Unclassified allowlisted unit gates PASS until a founder class is recorded"
        for needle, klass, why in FAMILY_RULES:
            if needle in lowered:
                unit_class = klass
                reason = why
                break
    gates = unit_class == CLASS_CORE_RUNTIME
    if unit_class == CLASS_INTENTIONALLY_DISABLED:
        expectation = "not_required"
    elif gates:
        expectation = "active"
    else:
        expectation = "observed"
    return {
        "unit_class": unit_class,
        "gates_overall_pass": gates,
        "class_reason": reason,
        "expectation": expectation,
    }
