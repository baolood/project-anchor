"""No-network HTTP client skeleton for the approved alternative testnet adapter.

This module intentionally performs no network I/O, reads no credentials, loads
no environment variables, and is not registered with any runtime runner.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Literal, Optional


AlternativeTestnetHttpStatus = Literal["ACCEPTED", "REJECTED", "FAILED"]
AlternativeTestnetHttpSide = Literal["BUY", "SELL"]
AlternativeTestnetHttpTransportStatus = Literal["ACCEPTED", "REJECTED", "NOT_EXECUTED"]


@dataclass(frozen=True)
class AlternativeTestnetHttpClientRequest:
    idempotency_key: str
    venue: str
    execution_mode: str = "testnet"
    symbol: str = "BTCUSDT"
    side: AlternativeTestnetHttpSide = "BUY"
    notional: str = "4"


@dataclass(frozen=True)
class AlternativeTestnetHttpBuiltRequest:
    method: str
    path: str
    venue: str
    execution_mode: str
    idempotency_key: str
    symbol: str
    side: AlternativeTestnetHttpSide
    notional: str
    client_order_ref: str
    body: dict[str, Any]


@dataclass(frozen=True)
class AlternativeTestnetHttpTransportInput:
    method: str
    path: str
    venue: str
    execution_mode: str
    idempotency_key: str
    client_order_ref: str
    body: dict[str, Any]


@dataclass(frozen=True)
class AlternativeTestnetHttpTransportResult:
    idempotency_key: str
    venue: str
    execution_mode: str
    status: AlternativeTestnetHttpTransportStatus
    network_sent: bool
    external_order_id: Optional[str]
    external_order_id_present: bool
    failure_family: Optional[str]
    failure_reason: Optional[str]


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


def _client_order_ref(request: AlternativeTestnetHttpClientRequest) -> str:
    seed = (
        f"{request.venue}:{request.execution_mode}:{request.idempotency_key}:"
        f"{request.symbol}:{request.side}:{request.notional}"
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"alt-testnet-local-{digest}"


class NoNetworkAlternativeTestnetHttpClient:
    """Return deterministic local fixture responses without opening a socket."""

    def build_order_request(
        self,
        request: AlternativeTestnetHttpClientRequest,
    ) -> AlternativeTestnetHttpBuiltRequest:
        client_order_ref = _client_order_ref(request)
        body = {
            "client_order_ref": client_order_ref,
            "execution_mode": request.execution_mode,
            "idempotency_key": request.idempotency_key,
            "notional": request.notional,
            "side": request.side,
            "symbol": request.symbol,
            "venue": request.venue,
        }
        return AlternativeTestnetHttpBuiltRequest(
            method="POST",
            path="/testnet/orders",
            venue=request.venue,
            execution_mode=request.execution_mode,
            idempotency_key=request.idempotency_key,
            symbol=request.symbol,
            side=request.side,
            notional=request.notional,
            client_order_ref=client_order_ref,
            body=body,
        )

    def build_transport_input(
        self,
        request: AlternativeTestnetHttpBuiltRequest,
    ) -> AlternativeTestnetHttpTransportInput:
        return AlternativeTestnetHttpTransportInput(
            method=request.method,
            path=request.path,
            venue=request.venue,
            execution_mode=request.execution_mode,
            idempotency_key=request.idempotency_key,
            client_order_ref=request.client_order_ref,
            body=dict(request.body),
        )

    def accepted_transport_result(
        self,
        transport_input: AlternativeTestnetHttpTransportInput,
        upstream_external_order_id: str,
    ) -> AlternativeTestnetHttpTransportResult:
        return AlternativeTestnetHttpTransportResult(
            idempotency_key=transport_input.idempotency_key,
            venue=transport_input.venue,
            execution_mode=transport_input.execution_mode,
            status="ACCEPTED",
            network_sent=False,
            external_order_id=upstream_external_order_id,
            external_order_id_present=True,
            failure_family=None,
            failure_reason=None,
        )

    def rejected_transport_result(
        self,
        transport_input: AlternativeTestnetHttpTransportInput,
    ) -> AlternativeTestnetHttpTransportResult:
        return AlternativeTestnetHttpTransportResult(
            idempotency_key=transport_input.idempotency_key,
            venue=transport_input.venue,
            execution_mode=transport_input.execution_mode,
            status="REJECTED",
            network_sent=False,
            external_order_id=None,
            external_order_id_present=False,
            failure_family="ALTERNATIVE_TESTNET_HTTP_TRANSPORT_REJECTED",
            failure_reason="alternative_testnet_http_transport_rejected",
        )

    def transport_not_executed_result(
        self,
        transport_input: AlternativeTestnetHttpTransportInput,
    ) -> AlternativeTestnetHttpTransportResult:
        return AlternativeTestnetHttpTransportResult(
            idempotency_key=transport_input.idempotency_key,
            venue=transport_input.venue,
            execution_mode=transport_input.execution_mode,
            status="NOT_EXECUTED",
            network_sent=False,
            external_order_id=None,
            external_order_id_present=False,
            failure_family="ALTERNATIVE_TESTNET_HTTP_TRANSPORT_NOT_EXECUTED",
            failure_reason="alternative_testnet_http_transport_not_executed",
        )

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
