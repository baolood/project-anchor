# Operator Domain DNS Deferral Rule V1

**Status:** DNS-deferral rule only. No DNS change, no ingress change, no runtime mutation, no live trading approval in this round.

**Owner:** **baolood** (Engineering / Operations / Release lead, interim).

**Date:** **2026-05-25**

## 1. Decision

Even though domain purchase is now allowed, DNS must still remain deferred until a separate approved rollout task begins.

Bounded decision:

```text
buying the domain is allowed now,
but connecting DNS is still out of scope
until a later dedicated ingress task is explicitly opened
```

## 2. Why DNS Is Still Deferred

Current posture is:

- first-controlled-send status: `ready_for_real_review`
- operator/reviewer hostname direction: defined
- landing surface direction: defined
- auth-boundary direction: defined
- live trading: `NO-GO`

That is enough for planning.
It is not enough for infrastructure mutation.

DNS creates real external meaning.
Once DNS points somewhere, rollout pressure often expands beyond the intended boundary.

## 3. What This Rule Allows

This rule allows:

- buying the domain
- reserving names conceptually
- documenting hostname intent
- documenting landing-surface scope
- documenting auth-boundary expectations

## 4. What This Rule Does Not Allow

This rule does not allow:

- adding DNS records
- connecting the domain to the host
- setting up reverse proxy routing
- opening firewall or ingress paths
- exposing `/ops`, `/commands`, or `/commands/[id]` over the public internet
- publishing raw backend access

## 5. Required Separation

The following must remain separate tasks:

1. domain purchase
2. hostname decision
3. landing-surface decision
4. auth-boundary decision
5. DNS implementation
6. ingress implementation

This round only covers the first four planning layers.
The last two remain deferred.

## 6. Pre-DNS Gates

Before any DNS task may start, all must remain true:

1. first-controlled-send status remains `ready_for_real_review`
2. operator/reviewer-only rollout plan still applies
3. hostname decision remains narrow
4. landing surface remains review-oriented
5. auth boundary remains explicit
6. live trading remains `NO-GO`
7. raw backend exposure remains forbidden

## 7. STOP Conditions

Stop immediately if:

- DNS starts being discussed as if it were only cosmetic
- DNS is being used to bypass ingress review
- DNS changes are proposed before auth posture is implementation-ready
- DNS meaning starts implying public release
- DNS meaning starts implying trading availability

## 8. Acceptance Checklist

This deferral rule is acceptable only if:

- it clearly states that domain purchase is allowed
- it clearly states that DNS remains deferred
- it clearly separates planning from infrastructure mutation
- it preserves operator/reviewer-only posture
- it keeps live trading `NO-GO`
- it blocks raw backend exposure

## 9. Rollback / Retreat

If DNS planning starts collapsing into infrastructure rollout:

1. retreat to the rollout, hostname, landing-surface, and auth-boundary decisions
2. stop all DNS/infrastructure discussion in the current task
3. reopen only as a dedicated rollout task with separate approval

Docs-only rollback:

```bash
cd /Users/baolood/Projects/project-anchor
git revert <commit>
git push origin main
```

## 10. One-Line Rule

```text
The domain may be bought now, but DNS must remain deferred until a separate approved rollout task explicitly handles ingress, auth implementation, and exposure review.
```
