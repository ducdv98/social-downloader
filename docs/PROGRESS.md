# Progress log

The handover between sessions. **Newest entry on top.** Keep each entry short.

## Current status

- **Phase:** 1 (URL pipeline), in progress. Items 1-3 done (error codes, `alias_url`, `clean_url`).
- **Next step:** Phase 1, item 4: host → service key (tldextract), plus subdomain and TLD checks. Cobalt reference: `getHostIfValid`, `url.js:169-182`.
- **Open questions:** (1) Should URL errors be returned (cobalt-style result type) or raised (typed exception carrying an `ErrorCode`)? Decide when writing `extract`. (2) `alias_url`/`clean_url` use hardcoded host sets (`YOUTUBE_HOSTS`, `QUERY_WHITELIST`); item 4 should replace them with a service lookup.

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
