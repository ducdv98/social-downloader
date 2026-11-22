# cobalt notes (reference summary)

These notes summarise how cobalt's API works, as a reference for the Python port.
Source: `/Users/ducdv/opensources/cobalt` (read-only). Paths below are relative to `api/src/`.

## Big picture

- `POST /` **thinks**: it validates the request, extracts the media info, decides an action and returns JSON.
- `GET /tunnel` **does the heavy work**: it streams bytes, either proxied directly or piped through ffmpeg.
- Each response has a `status`: `redirect` (the client downloads straight from the site, free for us), `tunnel` (we relay or process the bytes), `picker` (several items to choose from), `local-processing` (the client processes it locally), or `error`.
- Errors are dotted codes plus a `context`, e.g. `error.api.link.unsupported` with `{service}`. HTTP 400 means a user error, 500 critical, 429 rate limited.

## Request flow

1. The middleware chain checks content type, rate limits and auth (`core/api.js`).
2. The body is validated with a strict schema where only `url` is required (`processing/schema.js`).
3. The URL pipeline (`processing/url.js`):
   1. `aliasURL` normalizes aliases such as x.com.
   2. `cleanURL` strips the query (per-service whitelist), hash, port, credentials and trailing slash.
   3. The host is split with psl, and the second-level domain becomes the service key.
   4. Subdomain, TLD and enabled checks run.
   5. Patterns are tried in order; the first match wins (`service-config.js`).
   6. A tester sanity-checks the matched params (`service-patterns.js`).
4. `processing/match.js` dispatches to the extractor in `processing/services/<name>.js`.
5. `processing/match-action.js` decides what to do with the result (see the action decider below).

## Extractors

- Contract: they return `{urls, filename, audioFilename, headers, fileMetadata, subtitles, isHLS, picker, bestAudio, ...}` or `{error}`. They **never throw**.
- Techniques, from easiest to hardest:
  1. Public API (streamable, bluesky).
  2. Scraping embedded page JSON (TikTok `__UNIVERSAL_DATA_FOR_REHYDRATION__`).
  3. A private API with tokens (twitter guest token + GraphQL, reddit OAuth).
  4. Client emulation (youtube).
- Twitter flow: cached guest token → GraphQL → retry once on 403/429 → syndication fallback.
- Cookies are kept per service (`processing/cookie/`), updated from Set-Cookie and saved every 60s.
- `originalRequest` allows a "transplant": re-run the extractor when an upstream URL expires mid-stream.

## Action decider (pure)

- Priority: photo → picker → gif (if `convertGif`) → audio → mute → HLS → video.
- Then per-service rules. youtube and bilibili merge; vk, tiktok and ok proxy; instagram, facebook and others redirect; vimeo, rutube and loom depend on the result.
- `alwaysProxy` turns a redirect into a proxied tunnel. `localProcessing` (forced or preferred) applies to merge, remux, mute, audio and gif, but not HLS.
- Audio with format "best":
  - If the service offers a native format, proxy it; otherwise copy to m4a.
  - A specific requested format means re-encoding.
  - vk, ok and loom don't support audio.
- Cost per delivery type: redirect is free; proxy costs bandwidth; ffmpeg costs bandwidth and CPU.

## Tunnels (`stream/manage.js`, `misc/crypto.js`, `security/secrets.js`)

- Each tunnel gets an `id` (nanoid, 21 chars), an `iv` (16 B), a `secret` (32 B) and `exp = now + 90s`.
- The tunnel info is encrypted with AES-256-CBC using the secret as key and stored in Redis or memory with a TTL.
- `sig = HMAC-SHA256(salt, "id,exp,iv,secret")`.
- The URL carries `id, exp, sig, sec, iv`, so the key travels in the URL and the store holds only ciphertext.
- Verification order:
  1. Length checks fail with 400.
  2. HMAC check fails with 401.
  3. Store lookup fails with 404.
  4. Decryption fails with 500.
  5. Expiry check fails with 404.
- **Weak spots to improve in the port:**
  - The signature comparison uses `!==`; use `hmac.compare_digest`.
  - The store write isn't awaited.
  - It uses CBC instead of GCM.
  - The salt is random per process start; take it from config so restarts and multiple machines work.

## Media (`stream/ffmpeg.js`, `stream/internal.js`, `core/itunnel.js`)

- Remux and merge are cheap stream copies (`-c copy`). Video is never re-encoded.
- Operations:
  - merge: `-map 0:v -map 1:a -c copy`
  - mute: `-an`
  - audio: `-vn` plus copy or a bitrate
  - gif: palettegen
- Output goes to `pipe:3` and straight into the response. Nothing is written to disk.
- For MP4, `-movflags faststart+frag_keyframe+empty_moov` gives fragmented output, which can be streamed.
- An internal tunnel server on 127.0.0.1 feeds ffmpeg:
  - It injects the required headers.
  - It reads in 8 MB Range chunks (youtube, vk).
  - It transplants on 403.
  - It rewrites HLS playlists.
- Estimated content length = HEAD sizes × a multiplier.
- Cleanup: SIGTERM, then SIGKILL after 5s, on every exit path.

## Ops

- Auth modes:
  - API key (`Api-Key <uuid>`, with per-key limits and allowlists).
  - Session JWT (Turnstile check → `POST /session` → HS256 token valid for 120s).
  - Anonymous.
- Rate limits: `POST /` 20 per 60s, tunnel 40 per 60s, session 10 per 60s. Rate-limit keys are HMAC'd IPs, with IPv6 grouped by /56.
- Staying unblocked:
  - Cookies.
  - IPv6 rotation (freebind) and HTTP_PROXY support.
  - TLS cipher shuffling.
  - Per-service user agents.
- Scaling: a cluster of workers sharing a port, with secrets synced over IPC and Redis as shared state.
- Config is via env vars with hot reload (`core/env.js`).
- Gaps to fix in the port: observability, health checks, constant-time comparisons.
