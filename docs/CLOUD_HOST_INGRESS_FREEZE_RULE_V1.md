# Cloud host ingress freeze rule V1

**Status:** ingress freeze rule only - no real key, no external API call in this round, no live trading approval.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** 2026-05-24

**Scope:** define which ingress, exposure, or access-surface changes are explicitly forbidden during the bounded first-real-request preparation and review window for the cloud host.

This rule does not change actual ingress.
It freezes what must not be changed while the project is still proving the first guarded real testnet request.

## 1. Decision

During the first-real-request preparation and review window, ingress posture should be treated as frozen by default.

Meaning:

- do not widen exposure to “make testing easier”
- do not change host reachability assumptions mid-window
- do not use ingress changes as an ad hoc debugging shortcut

If a request window depends on changing ingress posture to proceed, result is:

```text
BLOCKED - do not proceed
```

## 2. What this freeze is for

This freeze exists to stop a common failure mode:

```text
something feels hard to inspect,
so someone widens ingress temporarily,
and the test boundary changes faster than the evidence boundary
```

That would make the first real request hard to review and easy to misinterpret.

The first bounded request should prove the canonical path under stable access assumptions, not under moving network assumptions.

## 3. Window covered by this freeze

This ingress freeze applies during:

- pre-request runtime verification
- guarded first-real-request enablement
- the request window itself
- immediate post-request review
- retreat / anomaly handling until the first request has been fully classified

The freeze ends only after:

- review is complete
- result is classified
- retreat or follow-up posture is explicitly decided

## 4. Explicitly forbidden ingress changes

During the freeze window, do not:

- open a new raw backend public port
- widen firewall rules for convenience
- change reverse-proxy routing in a way that alters current reachability
- introduce a new domain or public hostname
- switch from controlled/tunnel/operator access to broader public access
- expose runtime toggles or sensitive review surfaces through new ingress paths
- publish direct access to real helper or executor-specific endpoints

These are hard freeze rules, not suggestions.

## 5. Explicitly forbidden “debug convenience” moves

During the freeze window, do not:

- bypass the normal review path by directly exposing internal surfaces
- open a temporary port and promise to close it later
- broaden Nginx/proxy reachability to inspect behavior faster
- change host routing just to make `/commands` or `/ops` easier to reach
- let a one-off access workaround become the new assumed runtime posture

If visibility is too weak under the current boundary, that is a review finding, not a reason to widen ingress silently.

## 6. What remains allowed

This freeze does **not** forbid:

- read-only status checks
- controlled operator inspection through already-accepted access paths
- review of `/ops -> /commands -> /commands/[id]`
- log review under the current narrow posture
- explicit retreat back to `mock` or fail-closed posture

The rule is:

```text
inspect within the frozen boundary
do not change the boundary during the inspection window
```

## 7. Why the freeze matters

The project is still in a stage where:

- real testnet is guarded
- operator-only posture still matters
- logs and review artifacts are part of the evidence story
- domain/public ingress is still intentionally deferred

If ingress changes in the middle of the first-real-request window, the team may no longer know whether observed behavior came from:

- the canonical runtime path
- the command itself
- or the newly changed ingress posture

That ambiguity is not acceptable.

## 8. Exceptions

There should be no routine exceptions during the freeze window.

If an ingress change feels necessary, the correct interpretation is:

```text
the current bounded request should stop
and a separate approved ingress-change task should be opened
```

Do not mix “prove the first request” with “reconfigure how the host is reached.”

## 9. Minimum operator reminder

During the freeze window, the operator should be able to say:

```text
we are proving behavior under a fixed access posture
not using access changes as part of the experiment
```

If that statement does not remain true, stop the request workflow.

## 10. PASS criteria

This ingress freeze rule is `PASS` only if:

- no ingress widening happened during the window
- no new public surface was introduced
- no runtime-reachability assumption changed mid-review
- the request or review outcome can be interpreted without network-boundary drift

## 11. BLOCKED criteria

This ingress freeze rule is `BLOCKED` if:

- the operator believes ingress changes are needed to proceed
- review surfaces are only reachable by widening exposure
- a temporary access workaround is being considered as part of the same window
- the team cannot keep request proof and ingress change proof separate

This is a healthy stop condition, not lost momentum.

## 12. Stable status statement

At this point the correct ingress-freeze summary is:

```text
first real request must be reviewed under a fixed access posture
ingress widening is not part of the bounded request experiment
domain and public hostname work remain deferred
live trading: NO-GO
```

## 13. Minimal next bounded round

After this rule, the next natural host-related bounded round is:

```text
Cloud Host Domain Decision Gate V1
```

Scope:

```text
docs-only
define the exact conditions under which domain or broader public ingress work
stops being premature and becomes an allowed follow-up task
```
