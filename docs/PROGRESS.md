# Progress log

The handover between sessions. **Newest entry on top.** Keep each entry short.

## Current status

- **Phase:** 0 (Tooling and project skeleton), done. Phase 1 (URL pipeline) not started.
- **Next step:** Phase 1, first item: error codes as an enum (`link.invalid`, `link.unsupported`, `service.disabled`)
- **Open questions:** none

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
