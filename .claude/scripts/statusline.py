#!/usr/bin/env python3
"""Main statusLine — "ContextScout Active" bar + dev model line.

Payload confirmed empirically in this session (not just from the official
docs): model.id/display_name, effort.level, cost.total_cost_usd,
context_window.total_input_tokens/used_percentage,
context_window.current_usage.cache_read_input_tokens (nested, not top-level
as the official docs alone suggested). See docs/ai/claude-code-capabilities-verified.md.
"""
import json
import sys


def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("ContextScout Active")
        return

    model = payload.get("model", {})
    effort = payload.get("effort", {})
    cost = payload.get("cost", {})
    ctx = payload.get("context_window", {})
    cache_read = ctx.get("current_usage", {}).get("cache_read_input_tokens", 0)

    line = (
        f"🔎 ContextScout Active | dev: {model.get('display_name', '?')}"
        f" (effort:{effort.get('level', '?')})"
        f" | ${cost.get('total_cost_usd', 0):.2f}"
        f" | ctx {ctx.get('used_percentage', 0)}%"
        f" ({fmt_tokens(ctx.get('total_input_tokens', 0))}/{fmt_tokens(ctx.get('context_window_size', 0))})"
        f" | cache {fmt_tokens(cache_read)} read"
    )
    print(line)


if __name__ == "__main__":
    main()
