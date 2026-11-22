# Progress log

The handover between sessions. **Newest entry on top.** Keep each entry short.

## Current status

- **Phase:** 0 (Tooling and project skeleton), not started
- **Next step:** Phase 0, first item: `git init`, `.gitignore`, `uv init` with a `src/` layout
- **Open questions:**
  - Code ownership. Default: the owner writes all logic, and Claude writes boilerplate (config, CI, Dockerfile) only on request. Confirm or change this in `CLAUDE.md`.

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

### 2026-11-22: Study of cobalt (done in the cobalt repo)
- Done: a 10-chunk study of cobalt's API (what it does, architecture, API contract, URL pipeline, extractors, action decision, tunnels and security, media processing, ops, Python design). Set up these mentor docs.
- Learned: the two-phase design (`POST /` thinks, `/tunnel` streams); a pure core with impure edges; tunnel crypto; containers vs codecs. A summary is in `docs/cobalt-notes.md`.
- Questions / blockers: the code-ownership split (see above).
- Next: Phase 0.
