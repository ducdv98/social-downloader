# 0003: Two deliberate deviations from cobalt in the URL pipeline

- **Status:** Accepted
- **Date:** 2026-11-26

## Context
Running real links through the full pipeline (Phase 1, item 7) surfaced two cobalt
behaviours that are harmless in JS but wrong or unfriendly in the Python port.

1. **Twitter id is only length-checked.** `api/src/processing/service-patterns.js:74`
   is `pattern.id?.length < 20`, so `x.com/jack/status/abc` passes. The id later
   reaches `twitter.js:75`, `(Number(id) / 1e15) * Math.PI`, where `Number("abc")`
   is `NaN`. JS carries on, makes a useless request and fails at the network. In
   Python the equivalent `int("abc")` raises `ValueError`, which would be a 500.
2. **Alt domains match exact hosts only.** `aliasURL` in `url.js` checks
   `services.twitter.altDomains.includes(url.hostname)` with
   `altDomains: ["x.com", "vxtwitter.com", "fixvx.com"]`. `getHostIfValid`
   (`url.js:178`) allows `www` and `mobile` on `twitter.com`, but `www.x.com` and
   `mobile.x.com` are never aliased, so they fail with `link.invalid`. This
   looks like an oversight from when `altDomains` was added for the X rebrand.

## Options considered
1. **Keep parity** with cobalt in both cases. It's easy to compare, but it leaves a
   crash path for Phase 4 and rejects real links that users paste.
2. **Deviate in the pure layer.** Reject non-digit twitter ids in the tester, and
   alias `www.` / `mobile.` on alt domains.
3. **Deviate later.** Leave the pipeline alone and catch bad ids in the extractor.
   This spreads validation across layers.

## Decision
Option 2.
- The twitter tester also requires `[0-9]+` (ASCII only, so not `\d`, which
  matches Unicode digits like `١٢٣`). Failure is `link.unsupported`, as for any
  tester failure. YouTube is unchanged: its ids are base64url, not digits.
- `alias_url` rewrites a host to `twitter.com` only when its registered domain
  (tldextract `top_domain_under_public_suffix`) is in `TWITTER_ALT_HOSTS` **and**
  its subdomain is in `TWITTER_ALLOWED_SUBDOMAINS` (`""`, `www`, `mobile`). Any
  other subdomain is left alone. Aliasing replaces the whole netloc, so aliasing
  `api.x.com` would turn an invalid host into a valid one and skip the subdomain
  check that `api.twitter.com` fails.

## Consequences
- Extractors can assume a twitter `id` is all ASCII digits and fewer than 20 of them.
- `www.x.com`, `mobile.x.com`, `www.vxtwitter.com` and `mobile.fixvx.com` work.
  `api.x.com`, `www.mobile.x.com`, `notx.com` and `x.com.evil.com` stay rejected
  (guard rows in `tests/test_url.py`).
- Both spots carry a `Deviation from cobalt (ADR 0003)` comment, so nobody "fixes"
  them back to parity.
- `alias_url` now calls tldextract on every host (offline, cheap).
