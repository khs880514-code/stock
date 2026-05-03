from pathlib import Path


FORBIDDEN = [
    "AUTO_BUY",
    "AUTO_SELL",
    "MARKET_ORDER",
    "broker_order",
    "place_order",
    "execute_trade",
    "auto_trade",
    "numeric_confidence",
    "madness_weighted_score",
    "decision_score_buy",
]


def test_forbidden_strings_absent_from_runtime_code():
    root = Path(__file__).resolve().parents[1] / "app"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
    for token in FORBIDDEN:
        assert token not in combined

