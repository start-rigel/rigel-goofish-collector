# rigel-goofish-collector

Goofish market-reference collector adapted from `ai-goofish-monitor`.

## Language

Python

## Current Stage

Adapter foundation with upstream login-state preserved, plus a first Rigel-facing search and market-summary API.

## Intended Role

- keep Goofish login-state handling usable
- reuse upstream Playwright scraping behavior where valuable
- collect raw used-market product samples for PC parts
- aggregate those samples into canonical daily market-reference summaries
- provide reference prices for AI and for mixed/new-vs-used comparison

## Implemented

- vendored upstream `ai-goofish-monitor` core files under `vendor/ai_goofish_monitor`
- preserved upstream `LICENSE`
- FastAPI skeleton for Rigel
- login-state file management API
- default root-state promotion API
- runtime account-selection plan API based on upstream rotation logic
- login-state validation API for quick real-session checks
- `POST /api/v1/search` for used-market sample collection
- `POST /api/v1/market/summary` for immediate price aggregation over current samples
- optional PostgreSQL persistence into `products`, `price_snapshots`, and `jobs`
- conservative invalid-title filtering for obvious wanted posts, whole-PC listings, broken parts, and CPU/MB bundles

## Routes

- `GET /healthz`
- `GET /api/v1/state-files`
- `POST /api/v1/login-state`
- `POST /api/v1/login-state/default`
- `DELETE /api/v1/login-state/{file_name}`
- `POST /api/v1/runtime-plan`
- `POST /api/v1/validate-state`
- `POST /api/v1/search`
- `POST /api/v1/market/summary`

## Run Locally

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
python3 main.py
```

## Key Env Vars

- `RIGEL_HTTP_PORT`
- `RIGEL_GOOFISH_COLLECTOR_MODE=market_reference`
- `RIGEL_GOOFISH_STATE_DIR=state`
- `RIGEL_GOOFISH_ROOT_STATE_FILE=state/goofish_state.json`
- `RIGEL_GOOFISH_UPSTREAM_ENABLED=true`
- `RIGEL_GOOFISH_HEADLESS=true`
- `RIGEL_GOOFISH_SEARCH_TIMEOUT_MS=45000`
- `RIGEL_GOOFISH_BROWSER_CHANNEL=chromium`
- `RIGEL_GOOFISH_VALIDATION_KEYWORD=电脑 内存`
- `RIGEL_POSTGRES_DSN=...` enables persistence

## Example Requests

```bash
curl -X POST http://localhost:18085/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{"keyword":"DDR5 6000 32G","category":"RAM","limit":10}'
```

```bash
curl -X POST http://localhost:18085/api/v1/validate-state \
  -H 'Content-Type: application/json' \
  -d '{"account_state_file":"acc_1.json"}'
```

```bash
curl -X POST http://localhost:18085/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{"keyword":"DDR5 6000 32G","category":"RAM","limit":10,"persist":true}'
```

```bash
curl -X POST http://localhost:18085/api/v1/market/summary \
  -H 'Content-Type: application/json' \
  -d '{"keyword":"DDR5 6000 32G","category":"RAM","limit":10}'
```

## TODO / MOCK

- TODO: persist canonical mappings after `rigel-build-engine` normalizes titles into canonical part keys
- TODO: write daily aggregated canonical summaries into `part_market_summary` after canonical mapping is available
- TODO: verify real Goofish search against a valid login-state file in this narrowed adapter flow
