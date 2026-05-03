from __future__ import annotations

LLM_ASSIST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "ticker",
        "reason",
        "bear_case",
        "do_not_buy_if",
        "next_check",
        "confidence_label",
        "data_quality",
        "sources",
    ],
    "properties": {
        "ticker": {"type": "string"},
        "reason": {"type": "array", "items": {"type": "string"}},
        "bear_case": {"type": "array", "items": {"type": "string"}},
        "do_not_buy_if": {"type": "array", "items": {"type": "string"}},
        "next_check": {"type": "string"},
        "confidence_label": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "data_quality": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "price_data": {"type": "string"},
                "portfolio_data": {"type": "string"},
                "event_data": {"type": "string"},
                "news_context": {"type": "string"},
                "sentiment_data": {"type": "string"},
            },
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "url", "published_at"],
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "published_at": {"type": "string"},
                },
            },
        },
    },
}

