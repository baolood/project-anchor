"""Unit classes from the 2026-09-29 Vultr read-only production inventory.

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
REPORTS_DIR = "/var/lib/project-anchor/reports"

# Inventory section 3. Long-running enabled production processes.
# Comma-separated in the unit file; the parser also accepts the inventory's spaces.
RECOMMENDED_SERVICE_UNITS = (
    "nginx.service",
    "project-anchor-commercial-api.service",
    "project-anchor-payment-webhook.service",
    "project-anchor-whisper.service",
    "project-anchor-word-converter.service",
)
# Inventory section 3. Actively scheduled timers. None of these are CORE_RUNTIME.
RECOMMENDED_TIMER_UNITS = (
    "project-anchor-post-production-monitoring.timer",
    "project-anchor-kraken-public-shadow-paper-v1-1.timer",
    "project-anchor-evidence-reporter-v1.timer",
    "project-anchor-jev-forward-shadow-v1.timer",
    "project-anchor-jev-candidate-review-v1.timer",
    "project-anchor-kraken-forward.timer",
)
HOST_DEFAULT_SERVICES = RECOMMENDED_SERVICE_UNITS
HOST_DEFAULT_TIMERS = RECOMMENDED_TIMER_UNITS

# Shown in addition to the allowlist. Still fixed names, still systemctl show only.
# Omitted on purpose: the failed shadow-paper monitor, turtle timer, and Track B history.
OBSERVE_SERVICES = RECOMMENDED_SERVICE_UNITS + (
    "project-anchor-kraken-public-shadow-paper-v1-1.service",
    "project-anchor-post-production-monitoring.service",
    "project-anchor-evidence-reporter-v1.service",
    "project-anchor-jev-forward-shadow-v1.service",
    "project-anchor-jev-candidate-review-v1.service",
    "project-anchor-kraken-forward.service",
    "project-anchor-jev-forward-shadow-v2.service",
)
OBSERVE_TIMERS = RECOMMENDED_TIMER_UNITS + (
    "project-anchor-jev-forward-shadow-v2.timer",
)

# Exact units from the read-only inventory, with the role recorded there.
EXACT_CLASSES: dict[str, tuple[str, str]] = {
    "nginx.service": (
        CLASS_CORE_RUNTIME,
        "Inventory: enabled TLS edge; ops site proxies to the Docker backend on 127.0.0.1:8000",
    ),
    "project-anchor-commercial-api.service": (
        CLASS_AUXILIARY,
        "Inventory: commercial self-serve API on 127.0.0.1:8010, not the Anchor ops runtime",
    ),
    "project-anchor-payment-webhook.service": (
        CLASS_AUXILIARY,
        "Inventory: payment webhook adapter on 127.0.0.1:8001, not the Anchor ops runtime",
    ),
    "project-anchor-whisper.service": (
        CLASS_AUXILIARY,
        "Inventory: whisper voice server on 127.0.0.1:8088, not the Anchor ops runtime",
    ),
    "project-anchor-word-converter.service": (
        CLASS_AUXILIARY,
        "Inventory: document converter on 127.0.0.1:8791, not the Anchor ops runtime",
    ),
    "project-anchor-kraken-public-shadow-paper-v1-1.service": (
        CLASS_EVALUATION,
        "Inventory: timer-driven shadow paper V1.1 runtime",
    ),
    "project-anchor-kraken-public-shadow-paper-v1-1.timer": (
        CLASS_EVALUATION,
        "Inventory: schedules the shadow paper V1.1 runtime",
    ),
    "project-anchor-kraken-public-shadow-paper-v1-1-monitor.service": (
        CLASS_EVALUATION,
        "Inventory: shadow paper monitor was failed; excluded from the default allowlist",
    ),
    "project-anchor-evidence-reporter-v1.service": (
        CLASS_AUXILIARY,
        "Inventory: low-cost evidence reporter oneshot",
    ),
    "project-anchor-evidence-reporter-v1.timer": (
        CLASS_AUXILIARY,
        "Inventory: schedules the evidence reporter",
    ),
    "project-anchor-jev-candidate-review-v1.service": (
        CLASS_EVALUATION,
        "Inventory: JEV candidate review shadow oneshot",
    ),
    "project-anchor-jev-candidate-review-v1.timer": (
        CLASS_EVALUATION,
        "Inventory: schedules JEV candidate review",
    ),
    "project-anchor-jev-forward-shadow-v1.service": (
        CLASS_EVALUATION,
        "Inventory: JEV forward shadow V1 oneshot",
    ),
    "project-anchor-jev-forward-shadow-v1.timer": (
        CLASS_EVALUATION,
        "Inventory: schedules JEV forward shadow V1",
    ),
    "project-anchor-jev-forward-shadow-v2.service": (
        CLASS_INTENTIONALLY_DISABLED,
        "Inventory: unit file disabled until execute order; not required for health PASS",
    ),
    "project-anchor-jev-forward-shadow-v2.timer": (
        CLASS_EVALUATION,
        "Inventory: timer is armed while the v2 service stays execute-gated; omitted from the default timer allowlist",
    ),
    "project-anchor-kraken-forward.service": (
        CLASS_EVALUATION,
        "Inventory: public forward collector; unit file disabled, timer still live; optional oneshot",
    ),
    "project-anchor-kraken-forward.timer": (
        CLASS_EVALUATION,
        "Inventory: forward collector timer is active even though its unit file is disabled",
    ),
    "project-anchor-post-production-monitoring.service": (
        CLASS_AUXILIARY,
        "Inventory: read-only post-production monitoring oneshot",
    ),
    "project-anchor-post-production-monitoring.timer": (
        CLASS_AUXILIARY,
        "Inventory: schedules post-production monitoring; does not gate PASS",
    ),
    "project-anchor-kraken-turtle-eth-1h-shadow.timer": (
        CLASS_EVALUATION,
        "Inventory: inactive historical turtle shadow timer; excluded from the default allowlist",
    ),
    "docker.service": (
        CLASS_AUXILIARY,
        "Inventory: Docker containers are not systemd MCP targets; backend health is the loopback HTTP probe",
    ),
}

# Fallback for names that are not in the exact table. First match wins.
# jev-forward-shadow-v2 stays ahead of the generic shadow rule.
FAMILY_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "jev-forward-shadow-v2",
        CLASS_INTENTIONALLY_DISABLED,
        "Inventory: jev-forward-shadow-v2 is execute-gated and not required for health PASS",
    ),
    (
        "word-converter",
        CLASS_AUXILIARY,
        "Inventory: word-converter is a document utility, not the Anchor ops runtime",
    ),
    (
        "word_converter",
        CLASS_AUXILIARY,
        "Inventory: word-converter is a document utility, not the Anchor ops runtime",
    ),
    (
        "whisper",
        CLASS_AUXILIARY,
        "Inventory: whisper is a voice server, not the Anchor ops runtime",
    ),
    (
        "commercial",
        CLASS_AUXILIARY,
        "Inventory: commercial API is a product surface, not the Anchor ops runtime",
    ),
    (
        "payment",
        CLASS_AUXILIARY,
        "Inventory: payment webhook is a product adapter, not the Anchor ops runtime",
    ),
    (
        "evidence-reporter",
        CLASS_AUXILIARY,
        "Inventory: evidence reporter is auxiliary",
    ),
    (
        "post-production-monitoring",
        CLASS_AUXILIARY,
        "Inventory: post-production monitoring is auxiliary",
    ),
    (
        "turtle",
        CLASS_EVALUATION,
        "Inventory: turtle units are historical shadow workloads",
    ),
    (
        "track-b",
        CLASS_EVALUATION,
        "Inventory: Track B units are historical and are not production control targets",
    ),
    (
        "track_b",
        CLASS_EVALUATION,
        "Inventory: Track B units are historical and are not production control targets",
    ),
    (
        "prop-pe",
        CLASS_EVALUATION,
        "Inventory: prop-pe units are historical and are not production control targets",
    ),
    (
        "prop_pe",
        CLASS_EVALUATION,
        "Inventory: prop-pe units are historical and are not production control targets",
    ),
    (
        "recovery",
        CLASS_EVALUATION,
        "Inventory: recovery units are historical and are not production control targets",
    ),
    (
        "shadow",
        CLASS_EVALUATION,
        "Inventory: shadow workloads are evaluation",
    ),
    (
        "paper",
        CLASS_EVALUATION,
        "Inventory: paper workloads are evaluation",
    ),
    (
        "kraken-forward",
        CLASS_EVALUATION,
        "Inventory: Kraken forward collector is evaluation data collection",
    ),
)


def host_sidecar_enabled(env: Mapping[str, str]) -> bool:
    return (env.get(HOST_SIDECAR_ENV) or "").strip() == "1"


def classify_unit(name: str) -> dict[str, object]:
    """Classify one unit name.

    An allowlisted name that matches neither the exact table nor an inventory
    family stays CORE_RUNTIME so a new Anchor ops unit still gates PASS.
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
