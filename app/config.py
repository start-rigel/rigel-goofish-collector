from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    service_name: str
    http_port: int
    mode: str
    state_dir: Path
    root_state_file: Path
    upstream_enabled: bool
    run_headless: bool
    search_timeout_ms: int
    browser_channel: str


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> Config:
    state_dir = Path(os.getenv("RIGEL_GOOFISH_STATE_DIR", "state"))
    root_state_file = Path(
        os.getenv(
            "RIGEL_GOOFISH_ROOT_STATE_FILE",
            str(state_dir / "goofish_state.json"),
        )
    )
    return Config(
        service_name=os.getenv("RIGEL_SERVICE_NAME", "rigel-goofish-collector"),
        http_port=int(os.getenv("RIGEL_HTTP_PORT", os.getenv("RIGEL_GOOFISH_COLLECTOR_PORT", "8080"))),
        mode=os.getenv("RIGEL_GOOFISH_COLLECTOR_MODE", "market_reference"),
        state_dir=state_dir,
        root_state_file=root_state_file,
        upstream_enabled=_bool_env("RIGEL_GOOFISH_UPSTREAM_ENABLED", True),
        run_headless=_bool_env("RIGEL_GOOFISH_HEADLESS", True),
        search_timeout_ms=int(os.getenv("RIGEL_GOOFISH_SEARCH_TIMEOUT_MS", "45000")),
        browser_channel=os.getenv("RIGEL_GOOFISH_BROWSER_CHANNEL", "chromium"),
    )
