# 0002: Domain errors are returned as values, like cobalt

- **Status:** Accepted
- **Date:** 2026-11-25

## Context
cobalt's `extract` (`api/src/processing/url.js:193-231`) returns either
`{ host, patternMatch }` or `{ error: "link.invalid", context?: {...} }`. Its caller
(`api/src/core/api.js:248-263`) checks `"error" in parsed` and calls
`fail(res, \`error.api.${parsed.error}\`, parsed.context)`. The Python port has to choose
how the domain reports expected failures (`link.invalid`, `link.unsupported`,
`service.disabled`).

## Options considered
1. **Return a result union** (`Extracted | ExtractError`): this mirrors cobalt. Failures
   are explicit in the type, and mypy forces callers to handle them through
   `isinstance` narrowing. The cost is that each layer passes the error along by hand.
2. **Raise a typed exception carrying an `ErrorCode`**: this is idiomatic Python and
   keeps the happy path linear. One FastAPI handler would map it to JSON. The cost
   is that failures are invisible in the return type.

## Decision
Option 1. Expected domain failures are returned as a frozen `ExtractError(code,
context)` dataclass. Functions that can fail return `Success | ExtractError`.
Unexpected failures (bugs) still raise normally and become a generic error at the
API edge, the same way cobalt's `try/catch` in `match.js:335` maps them to
`fetch.critical`.

## Consequences
- Behaviour and code shape both match cobalt, so comparing the two is easy.
- mypy `--strict` flags any caller that uses a result without checking it first.
- The API layer adds the `error.api.` prefix, as `api.js:262` does. Domain codes stay bare.
- Each layer has a little more boilerplate (`if isinstance(r, ExtractError): return r`).
