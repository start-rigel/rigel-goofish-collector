# rigel-goofish-collector

Goofish market-reference collector adapted from `ai-goofish-monitor`.

## Language

Python

## Current Stage

Adapter foundation with upstream login-state and scraper code preserved.

## Intended Role

- keep Goofish login-state handling usable
- reuse upstream Playwright scraping behavior where valuable
- collect raw used-market product samples for PC parts
- later aggregate those samples into canonical daily market summaries
- provide reference prices for AI and for mixed/new-vs-used comparison

## Implemented

- vendored upstream `ai-goofish-monitor` core files under `vendor/ai_goofish_monitor`
- preserved upstream `LICENSE`
- FastAPI skeleton for Rigel
- login-state file management API
- runtime account-selection plan API based on upstream rotation logic

## Routes

- `GET /healthz`
- `GET /api/v1/state-files`
- `POST /api/v1/login-state`
- `DELETE /api/v1/login-state/{file_name}`
- `POST /api/v1/runtime-plan`

## Run Locally

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

## Key Env Vars

- `RIGEL_HTTP_PORT`
- `RIGEL_GOOFISH_COLLECTOR_MODE=market_reference`
- `RIGEL_GOOFISH_STATE_DIR=state`
- `RIGEL_GOOFISH_ROOT_STATE_FILE=state/goofish_state.json`
- `RIGEL_GOOFISH_UPSTREAM_ENABLED=true`

## TODO / MOCK

- TODO: wire vendored scraper into `POST /api/v1/search`
- TODO: expose `POST /api/v1/market/summary`
- TODO: narrow collection behavior to PC-part titles and price-reference output
