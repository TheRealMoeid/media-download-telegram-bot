# Phase 2 — Documentation updates (paste-in blocks)

Three small edits. I did not regenerate the full roadmap, modules, and claude files: they are long and I only have them as pasted context, so a full rewrite risks silent drift. Each block says exactly what to replace. After applying block 1, re-copy the root `PROJECT_ROADMAP.md` to `docs/PROJECT_ROADMAP.md`.

---

## Block 1 — `PROJECT_ROADMAP.md`

**1a. Replace the whole "## Tasks" section of "# 5. Phase 2" (from `## Tasks` down to just before `## Expected result`) with:**

```markdown
## Tasks

Phase 2 is split into six independently implementable sections (2A–2F). Out of scope for Phase 2: size limits, rate limits, concurrency, cancellation (Phase 3).

### 2A — Logging
- [ ] Console + rotating file logging in `logs/`.
- [ ] Silence `httpx`/`httpcore` INFO logs (they print the bot token in URLs); add a token-redaction filter.
- [ ] Optional `LOG_LEVEL` setting.
- [ ] Consistent, useful failure context; never log secrets.

### 2B — URL validation
- [ ] Extract a URL from surrounding text.
- [ ] Distinguish not-a-URL, unsupported host, and supported-host-wrong-shape (channel/playlist/profile/story).
- [ ] Specific translated message per reason; `detect_platform()` stays backward compatible.

### 2C — Failure classification
- [ ] Shared `FailureReason` categories (unavailable, age-restricted, geo-blocked, bot-check, network, FFmpeg, unknown).
- [ ] Map yt-dlp errors to categories; attach to existing exceptions without changing their types.

### 2D — Telegram-side failures and global error handler
- [ ] Distinguish send failures (too large, timeout, network) by detection only.
- [ ] Register a global error handler (log + translated generic message; never raises).
- [ ] Re-verify cleanup on every failure path.

### 2E — UX polish
- [ ] Specific translated messages per failure category, both languages.
- [ ] Remove dead `url.detected_youtube` key.
- [ ] Simple Retry for network-type failures (no Cancel; that is Phase 3).
- [ ] Remove stale menu keyboards where practical; native review of Persian wording.

### 2F — Test hardening
- [ ] Translation parity test (keys, languages, placeholders).
- [ ] Both-language flow tests; failure/cleanup tests for both platforms.
- [ ] Recount and record the real test total.
```

**1b. In "# 16. Current Development Position", at the end of the "Current status" paragraph, append:**

```markdown
**Phase 2 started.** Work is split into sections 2A–2F; see `PHASE_2_START_HERE.md` for order, file ownership and per-section briefs. First section: 2A (logging).
```

---

## Block 2 — `MODULES.md`

**In "## Currently active work", add as the first bullet:**

```markdown
- **Phase 2 — Reliability, Validation & UX — started.** Sections and ownership:
  - **2A Logging** — `run.py`, `config/settings.py`, `.env.example`. Not started.
  - **2B URL validation** — `downloader/manager.py` (+ `url.*` translation keys, minimal `handle_url_message` edit). Not started.
  - **2C Failure classification** — new `downloader/errors.py`, `downloader/instagram.py`, `downloader/youtube.py`. Not started. Adds a `reason` attribute to the downloader exceptions (contract change, flagged).
  - **2D Telegram-side failures + global error handler** — `services/video_service.py`, `run.py`, minimal error handler in `bot/handlers.py`. Not started. Depends on 2A. Merge 2A before 2D (both touch `run.py`).
  - **2E UX polish** — `bot/handlers.py`, `bot/keyboards.py`, `services/translations.py`. Not started. Depends on 2B, 2C, 2D. Run alone (highest-collision files).
  - **2F Test hardening** — `tests/` only. Not started.
  - 2A, 2B and 2C are parallel-safe. Merge 2B before 2E (both add translation keys).
```

**In "Shared / high-collision-risk files", append to the `run.py` bullet:** `Phase 2: 2A (logging) and 2D (error handler) both land here — merge 2A first.`

---

## Block 3 — `CLAUDE.md`

**3a. In §2, below the Phase 1 status table intro, add this line:**

```markdown
**Phase 2 (Reliability, Validation & UX) is in progress.** Six independent sections 2A–2F; see `PHASE_2_START_HERE.md` and `MODULES.md` "Currently active work". Update this section as each lands.
```

**3b. In §10 "Open items", add:**

```markdown
- **Security finding (Phase 2A):** `run.py` configures logging at INFO and PTB uses httpx, which logs request URLs containing the bot token. Fixed by 2A (httpx/httpcore to WARNING + redaction filter). If logs from before 2A were ever shared, rotate the token via @BotFather.
- **Verify before 2E:** the code snapshot reviewed on Oct 3 2026 had no `/menu` handlers or `tests/test_menu.py`, although this file says the menu was completed Oct 2. Confirm the menu code is on the branch Phase 2 starts from.
- **README.md is stale** about language switching (still lists it as not implemented). Update the status line, behavior table and Known limitations once the menu is confirmed present.
```

**3c. In §10, update the stale line about the test count:** after 2F, replace "exact total not recounted" in §6 with the real number from `pytest --collect-only -q`.
