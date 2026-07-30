# Post Production Alerting Readiness

Generated at: `2026-07-30T16:24:04Z`

## Result

- result: PASS
- status: POST_PRODUCTION_ALERTING_READY
- failure code: none
- inspect env requested: True

## Checks

- path: /etc/project-anchor/alerting.env
- exists: YES
- owner: root
- group: project_anchor_runtime
- mode: 640
- expected_owner: root
- expected_group: project_anchor_runtime
- expected_mode: 640
- owner_match: YES
- group_match: YES
- mode_match: YES
- telegram_notify_enabled_present: YES
- telegram_notify_enabled_valid: YES
- telegram_bot_token_present: YES
- telegram_chat_id_present: YES

## Boundary

- alerting_env_content_read: YES
- telegram_bot_token_value_disclosed: NO
- telegram_chat_id_value_disclosed: NO
- telegram_http_attempted: NO
- telegram_message_sent: NO
- production_env_read: NO
- production_request_sent: NO
- second_production_request_sent: NO
- canary_rerun: NO
- go_live: NO-GO
- live_trading: NO-GO
