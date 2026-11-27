# 0004: How the API contract is modelled

- **Status:** Proposed (the owner should review and accept it)
- **Date:** 2026-11-27

## Context
Phase 2 ports cobalt's request schema (`api/src/processing/schema.js`, written in zod),
its response shapes (`createResponse` in `processing/request.js`), and its error codes
(`fail` in `core/api.js`) to pydantic. A one-to-one copy doesn't fit our layered design
(ADR 0001), and some zod and pydantic behaviours differ.

## Options considered
1. **Copy cobalt one-to-one.** The URL would be normalized inside the schema (cobalt uses
   `.transform(normalizeURL)`), option values would be StrEnums, and all error codes would
   go in one enum. That's simple to compare with cobalt, but it puts domain logic inside a
   framework model, and digit values such as `"1080"` need awkward enum names.
2. **Keep the shape check separate from the logic.** The pydantic models only check shape
   and types, the option values are `Literal` type aliases in the domain, and the error
   codes are split by layer.

## Decision
Option 2:
- `api/schemas.py` holds the request model, the response models and the `ApiResponse`
  discriminated union (on `status`). The request model checks that `url` is a non-empty
  string and nothing more. The `alias_url` / `clean_url` / `extract` pipeline runs later,
  in the service layer.
- The option values are `type X = Literal[...]` aliases in `domain/options.py`, so the
  Phase 4 decider can share them without importing pydantic.
- The request model rejects snake_case keys (it validates by alias only) and uses
  `StrictBool`, to match zod's `.strict()` and `z.boolean()`. Strictness is set per field,
  not model-wide: in strict mode, pydantic would reject plain strings for enums when the
  input is a Python dict, which is what FastAPI passes in.
- `ErrorCode` (domain) keeps the pipeline errors. `ApiErrorCode` (`api/errors.py`) holds
  the web-layer errors (`link.missing`, `invalid_body`, `generic`, `fetch.critical.core`).
  The `error.api.` prefix is added only in `api/errors.py`.

## Consequences
- The domain stays free of pydantic, and the option types are checked by mypy
  (`--strict-equality` catches typos).
- A malformed URL that makes `urlsplit` raise `ValueError` is no longer caught by the
  schema, as cobalt's `new URL()` is. The service layer must catch it and return
  `link.invalid`. This is still open.
- Two fields need explicit aliases because `to_camel` can't produce cobalt's spelling:
  `youtubeHLS` and `isHLS`. The metadata keys are not camelCase (`album_artist`), so
  `FileMetadata` doesn't use the camelCase base class.
