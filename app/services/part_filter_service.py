from __future__ import annotations

from typing import Optional


COMMON_REJECT_MARKERS = (
    "求购",
    "求收",
    "收一个",
    "收个",
    "蹲一个",
    "蹲个",
    "换物",
    "置换",
    "交换",
    "求租",
    "出租",
)

WHOLE_PC_MARKERS = (
    "整机",
    "主机",
    "台式机",
    "全套",
    "配置单",
)

BROKEN_ITEM_MARKERS = (
    "坏",
    "故障",
    "不亮",
    "不开机",
    "尸体",
    "维修",
    "修过",
    "待修",
)

IRRELEVANT_MARKERS = (
    "显示器",
    "键盘",
    "鼠标",
    "笔记本",
)


def reject_reason(title: str, category: str) -> Optional[str]:
    normalized = (title or "").strip().lower()
    if not normalized:
        return "empty_title"

    for marker in COMMON_REJECT_MARKERS:
        if marker in normalized:
            return "wanted_post"

    for marker in IRRELEVANT_MARKERS:
        if marker in normalized:
            return "irrelevant_item"

    if category.upper() != "CASE":
        for marker in WHOLE_PC_MARKERS:
            if marker in normalized:
                return "whole_pc"

    for marker in BROKEN_ITEM_MARKERS:
        if marker in normalized:
            return "broken_item"

    if category.upper() in {"CPU", "MB"} and ("板u" in normalized or "套板" in normalized):
        return "bundle_listing"

    if category.upper() == "GPU" and ("矿" in normalized or "挖矿" in normalized):
        return "gpu_risk_listing"

    return None


def is_valid_part_listing(title: str, category: str) -> bool:
    return reject_reason(title, category) is None
