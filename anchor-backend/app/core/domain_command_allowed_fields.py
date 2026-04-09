DOMAIN_COMMAND_ALLOWED_FIELDS = {
    "quote": ("command_type", "symbol"),
    "preview": ("command_type", "symbol", "side", "notional_usd", "price"),
    "order": ("command_type", "symbol", "side", "notional_usd", "price"),
    "cancel": ("command_type", "reason"),
}
