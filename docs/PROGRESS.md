# Progress log

The handover between sessions. **Newest entry on top.** Keep each entry short.

## Current status

- **Phase:** 1 (URL pipeline) done. Phase 2 (API contract) is next.
- **Next step:** Phase 2, item 1: the pydantic request model mirroring cobalt's schema (only `url` required).
- **Open questions:** (1) `_youtube_watch_url` always rewrites to `youtube.com`; cobalt keeps the subdomain (`music.youtube.com/watch?v=`). Harmless for `extract`; revisit if filenames or redirects care. (2) `urlsplit` raises `ValueError` on some malformed input (e.g. `https://[abc/`); decide in Phase 2 whether the request schema catches it, like cobalt's `new URL()` throwing in `schema.js`. (3) cobalt does `patternMatch.index - 1` on a string (JS coerces `"1"` to 0); the Phase 4 twitter extractor must convert with `int()` explicitly.
---

## Entry template

```
### YYYY-MM-DD: <short title>
- Done:
- Learned:
- Questions / blockers:
- Next:
```

---

### 2026-11-26: Phase 1 done, real-link pipeline tests, two deviations from cobalt
- Done: `PIPELINE_CASES`, 62 raw links (most real, from cobalt's `util/tests/{youtube,twitter}.json`) run through `_run = extract(clean_url(alias_url(url)))`. Two deviations from cobalt (ADR 0003): the twitter tester requires ASCII digits (`_DIGITS = re.compile(r"[0-9]+")`); `alias_url` also aliases `www.`/`mobile.` on alt domains via tldextract `subdomain` + `top_domain_under_public_suffix`, and leaves every other subdomain alone. Guard rows for `api.x.com`, `www.mobile.x.com`, `notx.com`, `x.com.evil.com`. 156 tests green, mypy clean.
- Learned: pure-layer tests can't know a video exists (cobalt's 400s for dead links come from the network); JS `Number("abc")` is `NaN`, Python `int("abc")` raises; `\d` matches Unicode digits (`١٢٣`), `[0-9]` or `re.ASCII` doesn't; `a and re.fullmatch(...)` returns `None`, not `False`, so wrap it with `is not None` or `bool()`; `is` vs `==` in tester tests caught it too; aliasing must never turn an invalid host into a valid one; TDD red → green; PEP 8 two blank lines before a top-level `def`.
- Questions / blockers: see Open questions (3 is new).
- Next: Phase 2, item 1 (request model).

### 2026-11-26: Phase 1, pattern matcher, `extract`, param testers
- Done: `compile_pattern` (cobalt `":user/status/:id"` → regex via `re.split` with a capture group, `re.escape`, named groups). `ServiceConfig.patterns` (compiled once at import through `_patterns`) and a required `tester` field. `ExtractError` (in `errors.py`) and `Extracted` frozen dataclasses. `extract(url, enabled_services)` returns `Extracted | ExtractError` (ADR 0002): `LINK_INVALID`, `SERVICE_DISABLED`, first match wins, tester failure or no match → `LINK_UNSUPPORTED` with `{"service": key}`. Fixed a music.youtube.com bug: `QUERY_WHITELIST` and the youtube alias are now keyed by service key via `_service_key` (`YOUTUBE_HOSTS` removed). 79 tests green, mypy clean.
- Learned: regex metacharacters and `re.escape`; `(?P<name>...)` and `groupdict`; `^` inside `[]` means NOT; `fullmatch` as the anchor; the `r""` prefix only applies to literals; `tuple[X, ...]`, `*args`, dataclass field order; `field(default_factory=dict)`; frozen protects the reference, not the value; union returns and `isinstance` narrowing; JS `url.search` vs Python `query`; `Callable` and `lambda`; `a and b` returns an operand; `in` / `.get` / `d[k]` and mypy narrowing; JS `?.` is not `.get(k, "")`; watch IDE auto-imports.
- Questions / blockers: see Open questions. A correction from this session: cobalt's testers are length caps only, and they don't resolve pattern ambiguity.
- Next: Phase 1, item 7 (real-link test cases).

### 2026-11-24: Phase 1, `get_host_if_valid`
- Done: added `tldextract` (offline: `TLDExtract(suffix_list_urls=())`). Frozen `ServiceConfig` dataclass (`tld="com"`, `subdomains: frozenset[str] | Literal["*"]`) and a `SERVICES` dict (youtube, twitter). `get_host_if_valid(url) -> str | None` checks the sld, then the tld, then the subdomain; `""` and `www` are always allowed. 19-row `HOST_CASES` table. 48 tests green, mypy clean.
- Learned: subdomain / SLD / TLD / public suffix (`co.uk`); `tldextract` gives `""` for a missing subdomain; guard clauses; `dict.get` returning `None`; narrowing (`is None`, `!= "*"` inside `and`); `in` on a `str` is a substring check; shadowing and `UnboundLocalError` (ruff F823); tuple vs frozenset annotations; `urlsplit().hostname` lowercases and can be `None`; mypy found the same bug as the tests, and more.
- Questions / blockers: none new. `hostname.lower()` is redundant (optional cleanup).
- Next: Phase 1, item 5 (pattern table and matcher).

### 2026-11-23: Phase 1, error codes, `alias_url`, `clean_url`
- Done: `ErrorCode` StrEnum in `domain/errors.py` (values `link.invalid`, `link.unsupported`, `service.disabled`). `alias_url` in `domain/url.py` (x.com/vxtwitter/fixvx → twitter.com, youtu.be and shorts/live → `youtube.com/watch?v=`). `clean_url` (per-host query whitelist as a `dict`, strips credentials, port, fragment, trailing slash, first value wins). `tests/test_url.py` with 15 alias rows and 13 clean rows via `parametrize`. 29 tests green, ruff and mypy clean.
- Learned: `StrEnum` (name vs value; a dot can't be in an identifier); dot = attribute access; `urlsplit` and immutable `SplitResult` with `_replace` / `urlunsplit`; `quote` vs `urlencode`; `parse_qs` (dict of lists) vs `parse_qsl` (list of pairs); `frozenset`, `dict.fromkeys`, `**` unpacking; list slicing never raises (`[:1]`); `str.removesuffix` vs `removeprefix`; total pure functions; mypy catching what tests miss and tests catching what mypy misses (`v[:1]` on a string); `pytest.param(id=...)`; write the test table first.
- Questions / blockers: return vs raise for URL errors (see Open questions). Pipeline order is alias first, then clean, which is why the whitelist needs no `x.com`.
- Next: Phase 1, item 4 (host → service key with tldextract).

### 2026-11-22: Phase 0, tooling skeleton
- Done: `uv init --package` (src layout), `requires-python >=3.12`, `.gitignore`, ruff (E,F,I,UP,B), mypy strict, pytest smoke test with `capsys`, pre-commit (ruff + local mypy hook), GitHub Actions CI with a 3.12/3.14 matrix, README. Committed and pushed.
- Learned: venv and `uv`; `src/` layout and editable installs; linter vs formatter; `requires-python` vs `.python-version`; type hints are ignored at runtime, mypy enforces them; pytest fixtures as dependency injection; git hooks, and `--all-files` only sees tracked files; keeping pre-commit and `uv.lock` versions in sync.
- Questions / blockers: none. CI result was reported green by the owner.
- Next: Phase 1, error codes enum.

### 2026-11-22: Study of cobalt (done in the cobalt repo)
- Done: a 10-chunk study of cobalt's API (what it does, architecture, API contract, URL pipeline, extractors, action decision, tunnels and security, media processing, ops, Python design). Set up these mentor docs.
- Learned: the two-phase design (`POST /` thinks, `/tunnel` streams); a pure core with impure edges; tunnel crypto; containers vs codecs. A summary is in `docs/cobalt-notes.md`.
- Questions / blockers: the code-ownership split (see above).
- Next: Phase 0.
