# ADR-0001: Command Domain Contract Is Independent of API Contracts

## Status
Accepted

## Context
Project Anchor introduces a Command abstraction to coordinate work across
backend APIs, workers, and the console UI.

Early iterations attempted to model Command together with HTTP API
request/response schemas (e.g. POST /commands body, GET /commands/{id} response).
This led to ambiguity about what a Command "is" versus how it is transported
over the network.

## Decision
We define Command as a **domain-level contract**, independent of any API
request/response shape.

- `Command` represents a unit of intent and execution lifecycle.
- HTTP API schemas (create request, create response, list/get response)
  are considered **transport-layer concerns**.
- The domain Command schema lives in `docs/contracts/command.schema.json`
  and is shared across backend, workers, and UI.

## Consequences
- Backend, worker, and console share a single, stable definition of Command.
- API evolution (versioning, headers, pagination, idempotency) does not
  contaminate the domain model.
- Tooling and AI assistants are constrained from reshaping the core model
  based on transport convenience.

This decision intentionally favors long-term correctness and clarity over
short-term implementation convenience.
