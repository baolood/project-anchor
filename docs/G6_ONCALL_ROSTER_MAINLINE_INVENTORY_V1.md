# G6 On-call Roster Mainline Inventory V1
## 1. Current go-live hard gate state
- G1 — Deployment and rollback drills pass: DONE
- G2 — P0/P1 alerting verified: DONE
- G3 — Backup/restore drill within RPO/RTO: DONE
- G4 — Security review complete: DONE
- G5 — Capacity/stress test at target load pass: DONE
- G6 — On-call roster + incident SOP active: NOT_DONE
## 2. Current boundary
- go-live: NO-GO
- real external request: NOT AUTHORIZED
- live trading: NO-GO
## 3. Selected next mainline
- Selected next hard gate: G6 — On-call roster + incident SOP active
- This is the only selected next mainline.
- Do not start canary, release freeze, go/no-go review, production launch, real external request, or live trading before G6 is complete.
## 4. Current G6 evidence state
Known current state:
- ON_CALL_SOP.md exists: YES
- incident SOP drafted: YES
- alerting path verified: YES
- Telegram alert receipt proven: YES
- active on-call roster proven: NO
- escalation path proven: NO
- T-2/T-1 operational readiness proven: NO
- G6 ready for DONE: NO
## 5. Missing evidence
G6 cannot move to DONE until the project records non-secret evidence for:
- active primary operator
- active backup / escalation contact, or explicit solo-operator exception
- on-call coverage window
- alert receipt path
- incident acknowledgement expectation
- escalation trigger
- incident SOP location
- emergency stop / no-go authority
- go-live boundary remains NO-GO until final review
## 6. Required G6 inventory questions
Before activation, answer:
1. Who is primary on-call?
2. Is there a backup/escalation contact?
3. If solo-operator mode remains, is that explicitly accepted?
4. What is the on-call coverage window?
5. What alert channel is active?
6. What is the expected acknowledgement time?
7. What incidents trigger escalation?
8. Who has stop/no-go authority?
9. Which SOP/runbook is authoritative?
10. What evidence proves the roster is active?
## 7. Minimum future G6 scope
The future G6 activation must prove:
- roster identity
- contact method
- alert channel
- acknowledgement rule
- escalation rule
- SOP reference
- emergency stop authority
- G6 final verdict
It must not:
- authorize go-live
- authorize real external request
- authorize live trading
- expose personal secrets
- expose API tokens
- require production traffic
## 8. Mandatory stop conditions
Stop if:
- primary on-call is unclear
- backup/escalation posture is unclear
- solo-operator exception is not explicitly accepted
- alert channel is not active
- acknowledgement path cannot be tested or evidenced
- SOP reference is missing
- stop/no-go authority is unclear
- any action would authorize go-live, real external request, or live trading
## 9. Status after this inventory
- G6 selected as next mainline: YES
- G6 inventory prepared: YES
- active roster confirmed: NO
- escalation path confirmed: NO
- SOP active confirmed: NO
- G6 ready for DONE: NO
- go-live: NO-GO
- real external request: NOT AUTHORIZED
- live trading: NO-GO
## 10. Explicit non-claims
- This inventory does not activate the roster.
- This inventory does not complete G6.
- This inventory does not authorize go-live.
- This inventory does not authorize real external requests.
- This inventory does not authorize live trading.
