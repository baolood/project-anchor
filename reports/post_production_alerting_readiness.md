# Post Production Alerting Readiness

Generated at: `2026-07-30T16:18:22Z`

## Result

- result: BLOCKED
- status: POST_PRODUCTION_ALERTING_READINESS_BLOCKED
- failure code: ALERTING_ENV_FILE_MISSING_OR_UNREADABLE_METADATA
- inspect env requested: False

## Checks

- path: /etc/project-anchor/alerting.env
- exists: NO
- owner: 
- group: 
- mode: 
- expected_owner: root
- expected_group: project_anchor_runtime
- expected_mode: 640
- owner_match: NO
- group_match: NO
- mode_match: NO
- telegram_notify_enabled_present: NOT_INSPECTED
- telegram_notify_enabled_valid: NOT_INSPECTED
- telegram_bot_token_present: NOT_INSPECTED
- telegram_chat_id_present: NOT_INSPECTED

## Boundary

- alerting_env_content_read: NO
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
