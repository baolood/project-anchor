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
AlternativeTestnetHttpPipelineStatus = Literal["BUILT", "SIGNED", "NOT_EXECUTED", "ACCEPTED", "REJECTED"]
AlternativeTestnetHttpRuntimeWiringStatus = Literal["DISABLED", "NOT_ENABLED", "NOT_WIRED"]
AlternativeTestnetHttpSigningStatus = Literal["SIGNED", "NOT_EXECUTED"]
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
class AlternativeTestnetHttpSigningMaterial:
    material_id: str
    authorization_header_value: str
    signature_value: str


@dataclass(frozen=True)
class AlternativeTestnetHttpSigningInput:
    method: str
    path: str
    venue: str
    execution_mode: str
    idempotency_key: str
    client_order_ref: str
    body: dict[str, Any]
    material_id: str


@dataclass(frozen=True)
class AlternativeTestnetHttpSigningResult:
    idempotency_key: str
    venue: str
    execution_mode: str
    status: AlternativeTestnetHttpSigningStatus
    method: str
    path: str
    client_order_ref: str
    body: dict[str, Any]
    material_id: Optional[str]
    authorization_header_value: Optional[str]
    signature_value: Optional[str]
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


@dataclass(frozen=True)
class AlternativeTestnetHttpPipelineResult:
    idempotency_key: str
    venue: str
    execution_mode: str
    status: AlternativeTestnetHttpPipelineStatus
    method: str
    path: str
    client_order_ref: str
    body: dict[str, Any]
    material_id: Optional[str]
    authorization_header_value: Optional[str]
    signature_value: Optional[str]
    network_sent: bool
    external_order_id: Optional[str]
    external_order_id_present: bool
    failure_family: Optional[str]
    failure_reason: Optional[str]


@dataclass(frozen=True)
class AlternativeTestnetHttpRuntimeWiringResult:
    idempotency_key: str
    venue: str
    execution_mode: str
    status: AlternativeTestnetHttpRuntimeWiringStatus
    disabled_reason: str
    disabled_stage: str
    runtime_path_enabled: bool
    composed_pipeline_executed: bool
    signing_executed: bool
    transport_executed: bool
    network_sent: bool
    external_order_id: Optional[str]
    external_order_id_present: bool
    failure_family: str
    failure_reason: str


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

    def runtime_enablement_minimal_result(
        self,
        request: AlternativeTestnetHttpClientRequest,
    ) -> AlternativeTestnetHttpRuntimeWiringResult:
        return self.runtime_not_enabled_result(request)

    def runtime_enablement_integration_disabled_result(
        self,
        request: AlternativeTestnetHttpClientRequest,
    ) -> AlternativeTestnetHttpRuntimeWiringResult:
        return self.runtime_not_wired_result(request)

    def runtime_disabled_result(
        self,
        request: AlternativeTestnetHttpClientRequest,
    ) -> AlternativeTestnetHttpRuntimeWiringResult:
        return self._runtime_wiring_disabled_shape(
            request=request,
            status="DISABLED",
            failure_family="ALTERNATIVE_TESTNET_HTTP_RUNTIME_DISABLED",
            failure_reason="alternative_testnet_http_runtime_disabled",
        )

    def runtime_not_enabled_result(
        self,
        request: AlternativeTestnetHttpClientRequest,
    ) -> AlternativeTestnetHttpRuntimeWiringResult:
        return self._runtime_wiring_disabled_shape(
            request=request,
            status="NOT_ENABLED",
            failure_family="ALTERNATIVE_TESTNET_HTTP_RUNTIME_NOT_ENABLED",
            failure_reason="alternative_testnet_http_runtime_not_enabled",
        )

    def runtime_not_wired_result(
        self,
        request: AlternativeTestnetHttpClientRequest,
    ) -> AlternativeTestnetHttpRuntimeWiringResult:
        return self._runtime_wiring_disabled_shape(
            request=request,
            status="NOT_WIRED",
            failure_family="ALTERNATIVE_TESTNET_HTTP_RUNTIME_NOT_WIRED",
            failure_reason="alternative_testnet_http_runtime_not_wired",
        )

    def _runtime_wiring_disabled_shape(
        self,
        request: AlternativeTestnetHttpClientRequest,
        status: AlternativeTestnetHttpRuntimeWiringStatus,
        failure_family: str,
        failure_reason: str,
    ) -> AlternativeTestnetHttpRuntimeWiringResult:
        return AlternativeTestnetHttpRuntimeWiringResult(
            idempotency_key=request.idempotency_key,
            venue=request.venue,
            execution_mode=request.execution_mode,
            status=status,
            disabled_reason=failure_reason,
            disabled_stage="runtime_wiring",
            runtime_path_enabled=False,
            composed_pipeline_executed=False,
            signing_executed=False,
            transport_executed=False,
            network_sent=False,
            external_order_id=None,
            external_order_id_present=False,
            failure_family=failure_family,
            failure_reason=failure_reason,
        )

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

    def build_signing_input(
        self,
        transport_input: AlternativeTestnetHttpTransportInput,
        material: AlternativeTestnetHttpSigningMaterial,
    ) -> AlternativeTestnetHttpSigningInput:
        return AlternativeTestnetHttpSigningInput(
            method=transport_input.method,
            path=transport_input.path,
            venue=transport_input.venue,
            execution_mode=transport_input.execution_mode,
            idempotency_key=transport_input.idempotency_key,
            client_order_ref=transport_input.client_order_ref,
            body=dict(transport_input.body),
            material_id=material.material_id,
        )

    def signed_request_result(
        self,
        signing_input: AlternativeTestnetHttpSigningInput,
        material: AlternativeTestnetHttpSigningMaterial,
    ) -> AlternativeTestnetHttpSigningResult:
        return AlternativeTestnetHttpSigningResult(
            idempotency_key=signing_input.idempotency_key,
            venue=signing_input.venue,
            execution_mode=signing_input.execution_mode,
            status="SIGNED",
            method=signing_input.method,
            path=signing_input.path,
            client_order_ref=signing_input.client_order_ref,
            body=dict(signing_input.body),
            material_id=material.material_id,
            authorization_header_value=material.authorization_header_value,
            signature_value=material.signature_value,
            network_sent=False,
            external_order_id=None,
            external_order_id_present=False,
            failure_family=None,
            failure_reason=None,
        )

    def signing_not_executed_result(
        self,
        transport_input: AlternativeTestnetHttpTransportInput,
    ) -> AlternativeTestnetHttpSigningResult:
        return AlternativeTestnetHttpSigningResult(
            idempotency_key=transport_input.idempotency_key,
            venue=transport_input.venue,
            execution_mode=transport_input.execution_mode,
            status="NOT_EXECUTED",
            method=transport_input.method,
            path=transport_input.path,
            client_order_ref=transport_input.client_order_ref,
            body=dict(transport_input.body),
            material_id=None,
            authorization_header_value=None,
            signature_value=None,
            network_sent=False,
            external_order_id=None,
            external_order_id_present=False,
            failure_family="ALTERNATIVE_TESTNET_HTTP_SIGNING_NOT_EXECUTED",
            failure_reason="alternative_testnet_http_signing_not_executed",
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

    def build_only_pipeline_result(
        self,
        request: AlternativeTestnetHttpClientRequest,
    ) -> AlternativeTestnetHttpPipelineResult:
        built = self.build_order_request(request)
        return AlternativeTestnetHttpPipelineResult(
            idempotency_key=built.idempotency_key,
            venue=built.venue,
            execution_mode=built.execution_mode,
            status="BUILT",
            method=built.method,
            path=built.path,
            client_order_ref=built.client_order_ref,
            body=dict(built.body),
            material_id=None,
            authorization_header_value=None,
            signature_value=None,
            network_sent=False,
            external_order_id=None,
            external_order_id_present=False,
            failure_family=None,
            failure_reason=None,
        )

    def signed_not_sent_pipeline_result(
        self,
        request: AlternativeTestnetHttpClientRequest,
        material: AlternativeTestnetHttpSigningMaterial,
    ) -> AlternativeTestnetHttpPipelineResult:
        built = self.build_order_request(request)
        transport_input = self.build_transport_input(built)
        signing_input = self.build_signing_input(transport_input, material)
        signed = self.signed_request_result(signing_input, material)
        return AlternativeTestnetHttpPipelineResult(
            idempotency_key=signed.idempotency_key,
            venue=signed.venue,
            execution_mode=signed.execution_mode,
            status="SIGNED",
            method=signed.method,
            path=signed.path,
            client_order_ref=signed.client_order_ref,
            body=dict(signed.body),
            material_id=signed.material_id,
            authorization_header_value=signed.authorization_header_value,
            signature_value=signed.signature_value,
            network_sent=False,
            external_order_id=None,
            external_order_id_present=False,
            failure_family=None,
            failure_reason=None,
        )

    def transport_not_executed_pipeline_result(
        self,
        request: AlternativeTestnetHttpClientRequest,
        material: AlternativeTestnetHttpSigningMaterial,
    ) -> AlternativeTestnetHttpPipelineResult:
        built = self.build_order_request(request)
        transport_input = self.build_transport_input(built)
        signing_input = self.build_signing_input(transport_input, material)
        signed = self.signed_request_result(signing_input, material)
        transport = self.transport_not_executed_result(transport_input)
        return AlternativeTestnetHttpPipelineResult(
            idempotency_key=transport.idempotency_key,
            venue=transport.venue,
            execution_mode=transport.execution_mode,
            status="NOT_EXECUTED",
            method=signed.method,
            path=signed.path,
            client_order_ref=signed.client_order_ref,
            body=dict(signed.body),
            material_id=signed.material_id,
            authorization_header_value=signed.authorization_header_value,
            signature_value=signed.signature_value,
            network_sent=False,
            external_order_id=None,
            external_order_id_present=False,
            failure_family=transport.failure_family,
            failure_reason=transport.failure_reason,
        )

    def accepted_pipeline_result(
        self,
        request: AlternativeTestnetHttpClientRequest,
        material: AlternativeTestnetHttpSigningMaterial,
        upstream_external_order_id: str,
    ) -> AlternativeTestnetHttpPipelineResult:
        built = self.build_order_request(request)
        transport_input = self.build_transport_input(built)
        signing_input = self.build_signing_input(transport_input, material)
        signed = self.signed_request_result(signing_input, material)
        transport = self.accepted_transport_result(transport_input, upstream_external_order_id)
        return AlternativeTestnetHttpPipelineResult(
            idempotency_key=transport.idempotency_key,
            venue=transport.venue,
            execution_mode=transport.execution_mode,
            status="ACCEPTED",
            method=signed.method,
            path=signed.path,
            client_order_ref=signed.client_order_ref,
            body=dict(signed.body),
            material_id=signed.material_id,
            authorization_header_value=signed.authorization_header_value,
            signature_value=signed.signature_value,
            network_sent=False,
            external_order_id=transport.external_order_id,
            external_order_id_present=transport.external_order_id_present,
            failure_family=None,
            failure_reason=None,
        )

    def rejected_pipeline_result(
        self,
        request: AlternativeTestnetHttpClientRequest,
        material: AlternativeTestnetHttpSigningMaterial,
    ) -> AlternativeTestnetHttpPipelineResult:
        built = self.build_order_request(request)
        transport_input = self.build_transport_input(built)
        signing_input = self.build_signing_input(transport_input, material)
        signed = self.signed_request_result(signing_input, material)
        transport = self.rejected_transport_result(transport_input)
        return AlternativeTestnetHttpPipelineResult(
            idempotency_key=transport.idempotency_key,
            venue=transport.venue,
            execution_mode=transport.execution_mode,
            status="REJECTED",
            method=signed.method,
            path=signed.path,
            client_order_ref=signed.client_order_ref,
            body=dict(signed.body),
            material_id=signed.material_id,
            authorization_header_value=signed.authorization_header_value,
            signature_value=signed.signature_value,
            network_sent=False,
            external_order_id=None,
            external_order_id_present=False,
            failure_family=transport.failure_family,
            failure_reason=transport.failure_reason,
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
