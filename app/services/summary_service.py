from __future__ import annotations

from statistics import median
from typing import Dict, List


def summarize_prices(keyword: str, category: str, items: List[Dict]) -> Dict:
    prices = sorted([float(item["price"]) for item in items if item.get("price") is not None])
    if not prices:
        return {
            "keyword": keyword,
            "category": category,
            "sample_count": 0,
            "latest_price": None,
            "avg_price": None,
            "median_price": None,
            "p25_price": None,
            "p75_price": None,
        }

    return {
        "keyword": keyword,
        "category": category,
        "sample_count": len(prices),
        "latest_price": prices[0],
        "avg_price": round(sum(prices) / len(prices), 2),
        "median_price": round(float(median(prices)), 2),
        "p25_price": round(_quantile(prices, 0.25), 2),
        "p75_price": round(_quantile(prices, 0.75), 2),
    }


def _quantile(sorted_prices: List[float], q: float) -> float:
    if len(sorted_prices) == 1:
        return float(sorted_prices[0])
    position = (len(sorted_prices) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(sorted_prices) - 1)
    fraction = position - lower
    return float(sorted_prices[lower] + (sorted_prices[upper] - sorted_prices[lower]) * fraction)
