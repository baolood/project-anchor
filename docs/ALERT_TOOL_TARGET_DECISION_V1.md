# Alert Tool Target Decision V1

## Status

- Decision type: tool-target decision only
- Concrete alerting vendor selected: NO
- Accepted P0/P1 target class defined: YES
- Week 3 alerting row closed by this document: NO
- Real external request authorized: NO
- Live trading: NO-GO

## Question

What kind of tool target is acceptable for the Week 3 alerting line, given the
current project posture?

More concretely:

- what is good enough for **P0/P1** paging?
- what is acceptable for **P2/P3** routing?
- what should be rejected as insufficient right now?

## Current baseline

The project already has:

- agreed SLI/SLO numbers in **`docs/SERVICE_SLI_SLO.md`**
- alert thresholds and routing expectations in **`docs/ALERTING_ROUTING.md`**
- on-call severity / escalation semantics in **`docs/ON_CALL_SOP.md`**
- synthetic checks active under the accepted operator-run cadence

What the project does **not** yet have:

- a bound concrete paging/chat tool
- live alert rules wired into a tool
- real acknowledgement evidence

## Decision

Decision:

1. **P0/P1 must eventually land on an ack-capable direct operator target**
2. **P2/P3 may use a lighter-weight ticket/backlog channel**
3. **GitHub-only / doc-only / CI-only visibility is not sufficient for P0/P1**
4. The project does **not** select a concrete external vendor in this step

This means the tool-target decision is now partially closed:

- acceptable target class: YES
- concrete vendor binding: still pending

## Accepted target class for P0/P1

For the current project phase, an acceptable P0/P1 target must be:

- direct to the named on-call operator
- visible on a primary operator device in near-real time
- acknowledgement-capable
- evidence-capable (timestamp, delivery, and ack record)
- reviewable after the fact

Examples of acceptable target classes:

- paging app with ack trail
- direct chat/notification tool with visible delivery + ack trail
- another bounded mechanism that produces equivalent delivery and ack evidence

The requirement is about the behavior, not the brand.

## Accepted target class for P2/P3

For P2/P3, the project may accept a lighter target, such as:

- ticket queue
- chat channel
- backlog item path

as long as:

- the owner is explicit
- the response target is explicit
- the channel is reviewable

## What is not sufficient

The following are **not** sufficient as the Week 3 P0/P1 tool target by
themselves:

- documentation only
- GitHub PR status only
- CI status only
- “someone will notice” as the routing mechanism
- a future plan to choose a tool later

These are useful supporting signals, but they do not satisfy the alerting row’s
actual acceptance bar.

## Why we are not binding a vendor yet

We are still in the go-live preparation phase, and this step stays docs-only on
purpose.

Choosing a concrete vendor or wiring a live tool would add:

- integration surface
- secrets / webhook / token surface
- ack test surface
- escalation-debug surface

Those are all real tasks, but they should happen in a separate, explicit
authorization step.

## Checklist impact

Current effect on Week 3:

- `Alert rules + routing implemented`: remain **`IN_PROGRESS`**

Reason:

- target class is now clearer
- but a concrete tool is still not selected
- rules are not yet wired
- ack evidence is not yet collected

## Recommended next task

Recommended next task:

- **`Alert Platform Selection Authorization Review`**

That next task should answer:

- whether the project now authorizes choosing and wiring a concrete tool
- which tool will be used for P0/P1
- which lighter path will be used for P2/P3
- what acknowledgement evidence must be captured

## Final decision result

- Accepted P0/P1 target class defined: YES
- Accepted P2/P3 target class defined: YES
- Concrete vendor selected: NO
- Week 3 alerting row ready for DONE now: NO
- Real external request authorized: NO
- Live trading: NO-GO
