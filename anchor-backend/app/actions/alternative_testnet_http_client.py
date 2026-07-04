"""No-network HTTP client skeleton for the approved alternative testnet adapter.

This module intentionally performs no network I/O, reads no credentials, loads
no environment variables, and is not registered with any runtime runner.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Literal, Optional


AlternativeTestnetHttpStatus = Literal["ACCEPTED", "REJECTED", "FAILED"]


@dataclass(frozen=True)
class AlternativeTestnetHttpClientRequest:
    idempotency_key: str
    venue: str
    execution_mode: str = "testnet"


@dataclass(frozen=True)
class AlternativeTestnetHttpClientResponse:
    idempotency_key: str
    venue: str
    execution_mode: str
    status: AlternativeTestnetHttpStatus
    failure_family: Optional[str]
    failure_reason: Optional[str]
    external_order_id: Optional[str]
    external_order_id_present: bool


def _fixture_external_order_id(request: AlternativeTestnetHttpClientRequest) -> str:
    seed = f"{request.venue}:{request.execution_mode}:{request.idempotency_key}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"alt-testnet-http-fixture-{digest}"


class NoNetworkAlternativeTestnetHttpClient:
    """Return deterministic local fixture responses without opening a socket."""

    def accepted_fixture_response(
        self,
        request: AlternativeTestnetHttpClientRequest,
    ) -> AlternativeTestnetHttpClientResponse:
        external_order_id = _fixture_external_order_id(request)
        return AlternativeTestnetHttpClientResponse(
            idempotency_key=request.idempotency_key,
            venue=request.venue,
            execution_mode=request.execution_mode,
            status="ACCEPTED",
            failure_family=None,
            failure_reason=None,
            external_order_id=external_order_id,
            external_order_id_present=True,
        )

    def rejected_fixture_response(
        self,
        request: AlternativeTestnetHttpClientRequest,
    ) -> AlternativeTestnetHttpClientResponse:
        return AlternativeTestnetHttpClientResponse(
            idempotency_key=request.idempotency_key,
            venue=request.venue,
            execution_mode=request.execution_mode,
            status="REJECTED",
            failure_family="ALTERNATIVE_TESTNET_HTTP_REJECTED",
            failure_reason="alternative_testnet_http_rejected",
            external_order_id=None,
            external_order_id_present=False,
        )

    def failed_fixture_response(
        self,
        request: AlternativeTestnetHttpClientRequest,
    ) -> AlternativeTestnetHttpClientResponse:
        return AlternativeTestnetHttpClientResponse(
            idempotency_key=request.idempotency_key,
            venue=request.venue,
            execution_mode=request.execution_mode,
            status="FAILED",
            failure_family="ALTERNATIVE_TESTNET_HTTP_FAILED",
            failure_reason="alternative_testnet_http_failed",
            external_order_id=None,
            external_order_id_present=False,
        )

    def unexpected_fixture_response(
        self,
        request: AlternativeTestnetHttpClientRequest,
    ) -> AlternativeTestnetHttpClientResponse:
        return AlternativeTestnetHttpClientResponse(
            idempotency_key=request.idempotency_key,
            venue=request.venue,
            execution_mode=request.execution_mode,
            status="FAILED",
            failure_family="ALTERNATIVE_TESTNET_HTTP_UNEXPECTED",
            failure_reason="alternative_testnet_http_unexpected",
            external_order_id=None,
            external_order_id_present=False,
        )
