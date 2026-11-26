# Roadmap

Each phase lists a **goal**, the **concepts** it teaches, the cobalt **reference** files, and the **done when** checklist.
Take one step per session. Tick boxes as you go.

---

## Phase 0: Tooling and project skeleton

**Goal:** an empty but professional Python project in which lint, type checks and tests all run.
**Concepts:** virtual environments, `pyproject.toml`, packages vs modules, `src/` layout, linting, static typing, CI.

- [x] `git init`, `.gitignore`, `uv init` with a `src/` layout
- [x] ruff (lint + format) configured in `pyproject.toml`
- [x] mypy in strict mode configured
- [x] pytest runs, with one trivial passing test
- [x] pre-commit hooks (ruff, mypy)
- [x] GitHub Actions CI: lint, types, tests
- [x] README: how to set up and run the checks

## Phase 1: URL pipeline (pure domain)

**Goal:** turn a raw URL into `(service, matched params)` or a typed error, with no network access.
**Concepts:** `urllib.parse`, `re` named groups, pure functions, `StrEnum`, dataclasses, `pytest.mark.parametrize`.
**Reference:** `api/src/processing/url.js`, `service-config.js`, `service-patterns.js`.

- [x] Error codes as an enum (`link.invalid`, `link.unsupported`, `service.disabled`)
- [x] `alias_url`: youtu.be, x.com → twitter.com, etc. (only the youtube and twitter cases so far; the rest arrive with their services)
- [x] `clean_url`: strip the query (with a per-service whitelist), hash, port, credentials and trailing slash (whitelist covers youtube and twitter only)
- [x] Host → service key (tldextract), plus subdomain and TLD checks (youtube and twitter configs only so far)
- [x] Pattern table and matcher (first match wins)
- [x] Per-service param testers (youtube and twitter only so far)
- [x] 50+ parametrized test cases taken from real links

## Phase 2: API contract

**Goal:** `POST /` validates the request and returns typed responses. Extraction is still stubbed.
**Concepts:** FastAPI, pydantic v2 (`extra="forbid"`, defaults, discriminated unions), exception handlers, dependency injection, `TestClient`.
**Reference:** `api/src/core/api.js`, `processing/schema.js`, `processing/request.js`, `docs/api.md`.

- [ ] Request model mirroring cobalt's schema (only `url` required)
- [ ] Response models: `redirect | tunnel | picker | local-processing | error`
- [ ] Error mapping: dotted code, `context`, HTTP 400/500
- [ ] Accept/Content-Type checks and a body size limit
- [ ] `GET /` returns instance info
- [ ] API tests covering every response type (using stubbed data)

## Phase 3: First extractor (redirect only)

**Goal:** a real streamable.com link returns a working `redirect` response.
**Concepts:** `async`/`await`, httpx `AsyncClient`, app lifespan, JSON parsing, timeouts.
**Reference:** `processing/services/streamable.js`, `processing/match.js`.

- [ ] `Extractor` Protocol and `ExtractResult` model
- [ ] Shared httpx client created in the app lifespan
- [ ] Streamable extractor
- [ ] Integration test with a recorded response (respx)
- [ ] End-to-end check with `curl`

## Phase 4: Extractor framework and action decider

**Goal:** a plugin registry, a pure action decider, and 3+ services.
**Concepts:** Protocols, registries, the strategy pattern, decision tables, scraping embedded JSON, token caching.
**Reference:** `processing/match-action.js`, `services/tiktok.js`, `services/twitter.js`, `processing/cookie/`.

- [ ] Extractor registry (service key → extractor)
- [ ] `decide(result, options) -> Plan`, pure, with a matrix of tests
- [ ] TikTok extractor (page-embedded JSON)
- [ ] Twitter extractor (guest token + GraphQL + fallback)
- [ ] Picker responses (multiple media items)
- [ ] Filename builder

## Phase 5: Tunnels

**Goal:** `tunnel` responses stream bytes through our server, with signed, expiring links.
**Concepts:** HMAC, AES-GCM, constant-time comparison, TTL stores, Redis, `StreamingResponse`, backpressure.
**Reference:** `api/src/stream/manage.js`, `stream/proxy.js`, `misc/crypto.js`, `security/secrets.js`, `store/`.

- [ ] `Store` Protocol with memory and Redis implementations
- [ ] Crypto helpers: AES-GCM encrypt/decrypt, HMAC sign/verify (`compare_digest`)
- [ ] `create_tunnel` and `verify_tunnel` with tests for tampering, expiry and missing entries
- [ ] `GET /tunnel` proxy streaming with the required upstream headers
- [ ] Client disconnect cancels the upstream request

## Phase 6: Media processing

**Goal:** merge, remux, mute, audio extraction and GIF conversion via ffmpeg, streamed with no temp files.
**Concepts:** containers vs codecs, `asyncio.create_subprocess_exec`, pipes, cancellation and cleanup, semaphores.
**Reference:** `api/src/stream/ffmpeg.js`, `stream/internal.js`, `core/itunnel.js`, `stream/shared.js`.

- [ ] ffmpeg runner (stdout pipe → response, kill on disconnect)
- [ ] Merge (video + audio, `-c copy`) and remux
- [ ] Mute and audio extraction (copy or re-encode, bitrate)
- [ ] GIF conversion
- [ ] Concurrency cap (`asyncio.Semaphore`) and an estimated content length
- [ ] Tests with real ffmpeg on tiny sample files

## Phase 7: Ops and security

**Goal:** production concerns: auth, rate limits, config, logs and metrics.
**Concepts:** middleware, pydantic-settings, JWT, rate-limit algorithms, structured logging, Prometheus.
**Reference:** `security/api-keys.js`, `security/jwt.js`, `security/turnstile.js`, `core/env.js`, `store/redis-ratelimit.js`.

- [ ] Settings from environment variables (disabled services, duration limit, …)
- [ ] Rate limiting per IP (IPv6 grouped by /56)
- [ ] API-key auth with per-key limits
- [ ] Optional session JWT
- [ ] structlog JSON logs, a `/health` endpoint, Prometheus metrics

## Phase 8: Deploy

**Goal:** run it like a real service.
**Concepts:** Docker multi-stage builds, non-root containers, uvicorn workers, shared state across workers.

- [ ] Dockerfile (with ffmpeg, a non-root user and a healthcheck)
- [ ] docker-compose with Redis
- [ ] Multiple workers sharing secrets and state through Redis and config
- [ ] Load-test smoke check

## Phase 9: Hard extractors (stretch)

**Goal:** the difficult services.
**Concepts:** client emulation, signature deciphering, HLS playlists, cookies and proxies, IP rotation.
**Reference:** `services/youtube.js`, `services/instagram.js`, `stream/internal-hls.js`.

- [ ] Instagram
- [ ] Reddit (OAuth, separate audio track → merge)
- [ ] YouTube (via a library such as `yt-dlp` internals or `pytubefix`; research first)
- [ ] HLS support
- [ ] Live test suite run on a schedule
