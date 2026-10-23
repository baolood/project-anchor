"""C9 authoritative sources as paths. They are not trade-ledger columns."""

from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = frozenset({"audit", "kill_switch", "deploy", "authorization"})

# Proposed register. Not created by this package.
PROPOSED_INCIDENT_REGISTER = (
    "affl-v2-official-ledger/governance/C9_INCIDENT_REGISTER.jsonl"
)


@dataclass(frozen=True)
class C9Source:
    source_id: str
    category: str
    path: str
    present_in_this_repo: bool
    proposed_register: bool = False
    in_trade_ledger: bool = False

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError(f"unknown C9 category: {self.category}")
        if self.in_trade_ledger:
            raise ValueError("C9 sources must not be stuffed into the trade ledger")
        if not self.path or self.path.startswith("http"):
            raise ValueError("C9 entries are doc or host paths, not URLs")


def authoritative_sources() -> tuple[C9Source, ...]:
    """Binding list for a future pass-line data-source table.

    Repo paths are files this checkout can point at. Host paths are the
    operational locations named by the readiness inventory. None of them
    are columns on a trade row.
    """
    return (
        C9Source(
            "audit_go_live_checklist",
            "audit",
            "docs/GO_LIVE_CHECKLIST.md",
            True,
        ),
        C9Source(
            "audit_recording_spec",
            "audit",
            "docs/ANCHOR_EVAL_RECORDING_INFRA_SPEC_V1.md",
            True,
        ),
        C9Source(
            "audit_host_reports",
            "audit",
            "/var/lib/project-anchor/reports/",
            False,
        ),
        C9Source(
            "audit_evidence_reporter",
            "audit",
            "/var/lib/project-anchor/evidence-reporter-v1/",
            False,
        ),
        C9Source(
            "audit_jev_authoritative_samples",
            "audit",
            "/var/lib/project-anchor/jev-forward-shadow-v2/jev-forward-authoritative-v2.jsonl",
            False,
        ),
        C9Source(
            "kill_switch_boundary_doc",
            "kill_switch",
            "docs/KILL_SWITCH_REAL_BOUNDARY_CHECK_V1.md",
            True,
        ),
        C9Source(
            "kill_switch_mcp_doc",
            "kill_switch",
            "anchor-backend/docs/ANCHOR_CONTROL_MCP_V1.md",
            True,
        ),
        C9Source(
            "kill_switch_host_sidecar_doc",
            "kill_switch",
            "anchor-backend/docs/ANCHOR_CONTROL_MCP_HOST_SIDECAR_V1.md",
            True,
        ),
        C9Source(
            "deploy_host_checkout",
            "deploy",
            "/opt/project-anchor/project-anchor",
            False,
        ),
        C9Source(
            "deploy_mcp_systemd_unit",
            "deploy",
            "/etc/systemd/system/anchor-control-mcp.service",
            False,
        ),
        C9Source(
            "deploy_mcp_nginx_snippet",
            "deploy",
            "/etc/nginx/snippets/anchor-control-mcp.conf",
            False,
        ),
        C9Source(
            "authorization_ledger_genesis",
            "authorization",
            "affl-v2-official-ledger/genesis/LEDGER_GENESIS.json",
            False,
        ),
        C9Source(
            "authorization_ledger_state",
            "authorization",
            "AFFL_V2_OFFICIAL_LEDGER_STATE.json",
            False,
        ),
        C9Source(
            "authorization_mcp_deploy_report",
            "authorization",
            "ANCHOR_CONTROL_MCP_V1_DEPLOY_REPORT.md",
            False,
        ),
        C9Source(
            "authorization_mcp_inventory",
            "authorization",
            "ANCHOR_CONTROL_MCP_V1_Production_Deployment_Inventory.md",
            False,
        ),
        C9Source(
            "authorization_pass_line_doc",
            "authorization",
            "PROJECT_ANCHOR_OFFICIAL_EVALUATION_PASS_LINE_V1.md",
            False,
        ),
        C9Source(
            "audit_incident_register_proposed",
            "audit",
            PROPOSED_INCIDENT_REGISTER,
            False,
            proposed_register=True,
        ),
    )
