# Progress log

The handover between sessions. **Newest entry on top.** Keep each entry short.

## Current status

- **Phase:** 1 (URL pipeline), in progress. Items 1-4 done (error codes, `alias_url`, `clean_url`, `get_host_if_valid`).
- **Next step:** Phase 1, item 5: pattern table and matcher (first match wins). Cobalt reference: `extract`, `url.js:193-225`, and `patterns` in `service-config.js`.
- **Open questions:** (1) Should URL errors be returned (cobalt-style result type) or raised (typed exception carrying an `ErrorCode`)? Decide when writing `extract`. (2) `alias_url`/`clean_url` still use hardcoded host sets (`YOUTUBE_HOSTS`, `QUERY_WHITELIST`); replace them with `SERVICES` lookups in item 5, when `ServiceConfig` gains `patterns`.

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
