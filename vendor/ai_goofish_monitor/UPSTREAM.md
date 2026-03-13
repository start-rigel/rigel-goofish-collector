# Upstream Source

This directory contains selected files copied from the MIT-licensed upstream project:

- Repository: https://github.com/Usagi-org/ai-goofish-monitor
- Purpose in Rigel: preserve login-state handling, account rotation, and scraper reference code while the service is narrowed to PC-part market summaries.

Vendored files are intentionally not exposed directly as the public API of `rigel-goofish-collector`.
Rigel wraps them behind its own `app/` service layer.
