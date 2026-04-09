DOMAIN_COMMAND_REQUIRED_FIELDS = {
    "quote": ("command_type", "symbol"),
    "preview": ("command_type", "symbol", "side", "notional_usd"),
    "order": ("command_type", "symbol", "side", "notional_usd"),
    "cancel": ("command_type", "reason"),
}
