# G6 Roster Activation Packet V1

## 1. Current G6 state

- `G6 — On-call roster + incident SOP active`: `NOT_DONE`
- G6 selected as next mainline: `YES`
- G6 inventory prepared: `YES`
- active roster confirmed: `NO`
- escalation path confirmed: `NO`
- SOP active confirmed: `NO`
- go-live: `NO-GO`
- real external request: `NOT AUTHORIZED`
- live trading: `NO-GO`

## 2. Current known evidence

Evidence already present in the repo:

- authoritative SOP document exists: `YES`
- SOP path: `docs/ON_CALL_SOP.md`
- incident severity matrix exists: `YES`
- P0/P1 acknowledgement expectations exist: `YES`
- alerting path verified: `YES`
- Telegram alert receipt proven: `YES`

Current known role posture from existing docs:

- primary on-call named: `YES`
- primary on-call identity: `baolood`
- interim backup identity exists in docs: `YES`
- interim backup identity: `baolood`
- stop / no-go authority named: `YES`
- stop / no-go authority identity: `baolood`

## 3. Activation packet contents fixed now

This packet fixes the minimum G6 evidence surface that the future activation task
must either confirm or explicitly fail:

- primary on-call identity
- backup / escalation posture
- solo-operator exception posture
- on-call coverage window
- alert channel
- acknowledgement expectation
- escalation trigger
- authoritative SOP reference
- emergency stop / no-go authority
- final G6 verdict

## 4. Current confirmed items

Based on the current repo evidence, the following are confirmed now:

- primary on-call identified: `YES`
- alert channel identified: `YES`
- alert channel: `Telegram for P0/P1`
- acknowledgement expectation identified: `YES`
- acknowledgement rule source: `docs/ON_CALL_SOP.md`
- stop / no-go authority identified: `YES`
- SOP reference identified: `YES`

## 5. Current unconfirmed items

The following are still not proven active:

- active roster confirmed: `NO`
- backup / escalation contact confirmed as active: `NO`
- solo-operator exception explicitly accepted: `NO`
- on-call coverage window fixed in activation evidence: `NO`
- T-2 / T-1 operational readiness proven: `NO`
- G6 ready for `DONE`: `NO`

## 6. Required future activation evidence

The future bounded activation task must record non-secret evidence for:

- primary on-call
- backup / escalation posture
- whether solo-operator mode is explicitly accepted
- coverage window
- active alert channel
- acknowledgement expectation
- escalation trigger
- emergency stop / no-go authority
- authoritative SOP path
- final PASS / FAIL verdict

## 7. Mandatory stop conditions

Stop the future activation task if:

- primary on-call identity is unclear
- backup / escalation posture is unclear
- solo-operator exception is still not explicitly accepted
- coverage window is not fixed
- alert channel cannot be shown as active
- acknowledgement path cannot be evidenced
- stop / no-go authority is unclear
- any step would authorize go-live, real external request, or live trading

## 8. Status after this packet

- roster activation packet prepared: `YES`
- primary on-call identified: `YES`
- alert channel identified: `YES`
- acknowledgement expectation identified: `YES`
- stop / no-go authority identified: `YES`
- backup / escalation contact confirmed as active: `NO`
- solo-operator exception explicitly accepted: `NO`
- on-call coverage window fixed: `NO`
- active roster confirmed: `NO`
- G6 ready for `DONE`: `NO`

## 9. Explicit non-claims

- this packet does not activate the roster
- this packet does not complete G6
- this packet does not authorize go-live
- this packet does not authorize real external requests
- this packet does not authorize live trading
