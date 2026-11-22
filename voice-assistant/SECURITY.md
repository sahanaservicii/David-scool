# Security Policy

## Supported scope
This project is a local/offline-first assistant framework. Security depends on deployment choices (network exposure, enabled providers, integrations).

## Security model and controls
- **Local by default**: web server binds to `127.0.0.1` unless explicitly configured with `server.allow_lan`.
- **No arbitrary shell from user text**: skills do not pass raw user input to shells. Calculator uses `ast` parsing (no `eval`).
- **App launch allowlist**: `app_control` only maps known app names to known binaries.
- **Homelab bridge**: invokes `homelab.py` with fixed argument sets derived from intent keywords (no user-controlled argv).
- **Static file serving**: path traversal mitigated via resolve + `relative_to` static directory check.
- **Input limits**: web API enforces request size and text/session length limits.
- **Secrets**: keep tokens/keys in `config/config.local.json` or environment variables with restricted permissions; never commit secrets.

## Recommendations for production/hardening
- Keep `server.allow_lan=false` unless needed; if exposed on LAN, use reverse proxy with TLS and authentication.
- Do not expose directly to the public internet.
- Review and restrict `search.searxng_url`, LLM `base_url`, and any integration endpoints (SSRF/trust boundary is operator-controlled config).
- Run under a non-root user where possible, with least-privilege filesystem access.
- Disable conversation logging if sensitive (`security.log_conversations=false`).
- Back up `data/assistant.db` securely; protect `config/config.local.json`.
- Validate/limit third-party models and plugins before enabling.

## Reporting
For local/private deployments, track issues in your own repository. Do not include secrets in reports.
