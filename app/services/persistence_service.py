from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json


@dataclass(frozen=True)
class PersistResult:
    job_id: str
    persisted_count: int


class PersistenceService:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def persist_search_result(self, payload: Dict[str, Any], summary: Optional[Dict[str, Any]] = None) -> PersistResult:
        if not self.dsn:
            raise ValueError("postgres dsn is required for persistence")

        now = datetime.now(timezone.utc)
        products: List[Dict[str, Any]] = payload.get("products", [])
        keyword = payload.get("keyword", "")
        category = payload.get("category", "")

        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                job_id = self._create_job(cur, keyword, category, payload, now)
                persisted_count = 0
                try:
                    for product in products:
                        product_id = self._upsert_product(cur, product, now)
                        self._insert_price_snapshot(cur, product_id, product, keyword, category, now)
                        persisted_count += 1
                    self._finish_job(cur, job_id, now, payload, summary, persisted_count, None)
                except Exception as exc:
                    self._finish_job(cur, job_id, now, payload, summary, persisted_count, str(exc))
                    raise
            conn.commit()
        return PersistResult(job_id=job_id, persisted_count=persisted_count)

    def _create_job(self, cur, keyword: str, category: str, payload: Dict[str, Any], now: datetime) -> str:
        cur.execute(
            """
            INSERT INTO jobs (job_type, status, source_platform, payload, result, scheduled_at, started_at)
            VALUES ('goofish_collect', 'running', 'xianyu', %s, %s, %s, %s)
            RETURNING id
            """,
            (Json({"keyword": keyword, "category": category, "limit": payload.get("limit", 0)}), Json({}), now, now),
        )
        row = cur.fetchone()
        return str(row["id"])

    def _finish_job(self, cur, job_id: str, now: datetime, payload: Dict[str, Any], summary: Optional[Dict[str, Any]], persisted_count: int, error_message: Optional[str]) -> None:
        status = "failed" if error_message else "succeeded"
        result = {
            "keyword": payload.get("keyword"),
            "category": payload.get("category"),
            "sample_count": payload.get("sample_count", 0),
            "persisted_count": persisted_count,
        }
        if summary is not None:
            result["summary"] = summary
        if error_message:
            result["error"] = error_message
        cur.execute(
            """
            UPDATE jobs
            SET status = %s,
                result = %s,
                finished_at = %s,
                error_message = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (status, Json(result), now, error_message, job_id),
        )

    def _upsert_product(self, cur, product: Dict[str, Any], now: datetime) -> str:
        external_id = product.get("item_id") or product.get("url") or product.get("title")
        cur.execute(
            """
            INSERT INTO products (
                source_platform, external_id, title, subtitle, url, image_url, shop_name, shop_type,
                seller_name, region, price, currency, availability, attributes, raw_payload,
                first_seen_at, last_seen_at, created_at, updated_at
            )
            VALUES (
                'xianyu', %s, %s, %s, %s, %s, %s, 'personal',
                %s, %s, %s, %s, 'unknown', %s, %s,
                %s, %s, NOW(), NOW()
            )
            ON CONFLICT (source_platform, external_id)
            DO UPDATE SET
                title = EXCLUDED.title,
                subtitle = EXCLUDED.subtitle,
                url = EXCLUDED.url,
                image_url = EXCLUDED.image_url,
                shop_name = EXCLUDED.shop_name,
                seller_name = EXCLUDED.seller_name,
                region = EXCLUDED.region,
                price = EXCLUDED.price,
                currency = EXCLUDED.currency,
                attributes = EXCLUDED.attributes,
                raw_payload = EXCLUDED.raw_payload,
                last_seen_at = EXCLUDED.last_seen_at,
                updated_at = NOW()
            RETURNING id
            """,
            (
                str(external_id),
                product.get("title", ""),
                product.get("keyword", ""),
                product.get("url", ""),
                product.get("image_url", ""),
                product.get("seller", ""),
                product.get("seller", ""),
                product.get("area", ""),
                product.get("price", 0),
                product.get("currency", "CNY"),
                Json(
                    {
                        "category": product.get("category", ""),
                        "keyword": product.get("keyword", ""),
                        "published_at": product.get("published_at"),
                        "tags": product.get("tags", []),
                    }
                ),
                Json(product.get("raw_payload", {})),
                now,
                now,
            ),
        )
        row = cur.fetchone()
        return str(row["id"])

    def _insert_price_snapshot(self, cur, product_id: str, product: Dict[str, Any], keyword: str, category: str, now: datetime) -> None:
        cur.execute(
            """
            INSERT INTO price_snapshots (product_id, source_platform, price, in_stock, captured_at, metadata)
            VALUES (%s, 'xianyu', %s, TRUE, %s, %s)
            """,
            (
                product_id,
                product.get("price", 0),
                now,
                Json({"keyword": keyword, "category": category, "tags": product.get("tags", [])}),
            ),
        )
