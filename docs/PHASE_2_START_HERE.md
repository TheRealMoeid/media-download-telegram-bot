# PHASE 2 — START HERE

Phase 2 = Reliability, Validation & UX. Six independent sections (2A–2F).
This file is your morning checklist plus a ready-to-paste brief for each section.

---

## 0. Your first 10 minutes tomorrow

1. **Check the menu code exists locally.** The `bot/handlers.py` I was shown has no `/menu`, no `handle_menu_navigation`, and there is no `tests/test_menu.py`, although the docs say the menu feature was finished on Oct 2. Run `git branch --show-current` and `git log --oneline -5`, and check that `/menu` is in `bot/handlers.py`. If it is missing, the menu work is on another branch and must be merged before 2E. Sections 2A–2D don't depend on it.
2. **Apply the doc updates** from `PHASE_2_DOC_UPDATES.md` (three small paste-in blocks: roadmap, modules, claude). Also re-copy the root `PROJECT_ROADMAP.md` to `docs/`.
3. **Run `pytest tests/ -v`** and confirm green before any Phase 2 work. This is the baseline.
4. **Create the integration branch** (suggested): `git checkout -b phase-2` from your current Phase 1 branch, then one short-lived branch per section (`p2a-logging`, and so on).
5. **Start with Section 2A.** Paste its brief (below) into a model session.

## Why 2A first

2A is small, fully independent, and fixes a real issue. `run.py` sets logging to INFO. python-telegram-bot uses httpx, and httpx logs request URLs at INFO, and Telegram API URLs contain your bot token (`.../bot<TOKEN>/getUpdates`). So your token is probably printed to your terminal on every poll right now. Please confirm by looking at your terminal output. If it shows up, treat that as a reason to do 2A first, and rotate the token if any of those logs were ever shared.

## Recommended order

```
2A Logging ─────────┐
2C Failure classes ─┼─(parallel-safe, disjoint files)─┐
2B URL validation ──┘                                  ├─> 2D ─> 2E (alone) ─> 2F
```

- **Run in parallel if you like:** 2A, 2B, 2C (different files; see ownership table).
- **Then:** 2D, which needs 2A's logging and decides the outcome shape 2E consumes.
- **Then:** 2E alone (it touches `handlers.py`, the highest-collision file).
- **Last:** 2F.

## File ownership (prevents collisions)

| Section | Owns | Must NOT touch |
|---|---|---|
| 2A | `run.py`, `config/settings.py`, `.env.example`, new logging helper | handlers, downloaders |
| 2B | `downloader/manager.py`, `tests/test_manager.py`, `url.*` keys in `translations.py`, minimal `handle_url_message` edit | downloaders, `video_service` |
| 2C | `downloader/errors.py` (new), `downloader/instagram.py`, `downloader/youtube.py`, their tests | `bot/*`, `translations.py` |
| 2D | `services/video_service.py`, error handler registration in `run.py`/`handlers.py` (minimal) | downloaders, `keyboards.py` |
| 2E | `bot/handlers.py`, `bot/keyboards.py`, `translations.py` | downloader internals |
| 2F | `tests/` only | production code |

Shared-file notes: 2A and 2D both touch `run.py` (run them sequentially or merge 2A first). 2B and 2E both add translation keys (merge 2B first and have 2E re-read the file). Any change to `requirements.txt` must be flagged to you, not made quietly.

## Decisions I need from you (defaults chosen, so "go" is enough)

1. **Outcome shape (affects 2C/2D/2E).** *Default:* keep `video_service` Telegram-free. Extend `DeliveryOutcome` handling so failures carry an optional generic `reason` string/enum (e.g. `"too_large"`, `"timeout"`, `"network"`, `"unavailable"`, `"unknown"`); the handler maps reasons to translated messages. Classification of Telegram exceptions happens in the handler-side `send_fn` wrapper, not in `video_service`.
2. **Retry/Cancel in 2E.** *Default:* add a simple **Retry** only for network-type failures; do **not** build Cancel (the roadmap puts cancellation in Phase 3).
3. **Persian wording.** *Default:* models draft it; you (or a native speaker) review once at the end of 2E.
4. **Log file location/size.** *Default:* `logs/bot.log`, rotating, 1 MB x 3 backups, level from optional `LOG_LEVEL` (default INFO).

---

## Brief template rules (apply to every brief)

Every session must first read, in full: `CLAUDE.md`, `AI_COLLABORATION.md`, `MODULES.md`, and the Phase 2 part of `PROJECT_ROADMAP.md`. Work from the actual file contents provided, never reconstructed layouts. Discuss options before writing code. Deliver complete replacement files (not patches), tests included, no real network calls in pytest. Update the docs listed in the handoff section before calling the work done. State plainly what was not done.

---

## BRIEF 2A — Logging

**Purpose:** failures are diagnosable from logs, and secrets never appear in them.

**Scope (may touch):** `run.py`, `config/settings.py` (optional `LOG_LEVEL`), `.env.example`, `tests/` for these.
**Out of scope:** handlers, keyboards, downloaders, `video_service`.

**Tasks**
- Configure logging to console plus a rotating file in `logs/` (`logs/` is gitignored).
- Set `httpx` and `httpcore` loggers to WARNING so Telegram URLs containing the token are never logged.
- Add a redaction safeguard (a logging filter that masks the bot token if it ever appears in a record) as a second line of defense.
- Ensure existing failure logs (`video_service`, `youtube`, `instagram`) are useful; do not edit those files here, only report gaps in the handoff notes.
- Never log the full yt-dlp options dict or the `.env` contents.

**Dependencies:** none.

**Done when**
- A test emits an httpx-style record containing the token and proves the captured output does not contain it.
- A test proves the file handler rotates (small max size in the test).
- `LOG_LEVEL` parsing is tested in `test_settings.py` (default, valid, invalid).
- Manual check: run the bot, send `/start`, confirm the terminal and `logs/bot.log` contain no token.

**Handoff:** update `CLAUDE.md` §2/§5/§7 (new setting, logging behavior), `MODULES.md` module 1 field list, `.env.example`, README config table.

---

## BRIEF 2B — URL validation

**Purpose:** reject bad input precisely instead of failing deep inside yt-dlp.

**Scope (may touch):** `downloader/manager.py`, `tests/test_manager.py`, `url.*` keys in `services/translations.py` (+ `test_translations.py`), and the minimal change in `handle_url_message` to use the new result.
**Out of scope:** downloaders, `video_service`, menu code.

**Tasks**
- Extract the first URL from a message that has surrounding text (users paste "check this https://...").
- Keep `detect_platform(url) -> Platform` and its 24 tests passing unchanged (backward compatible).
- Add a richer function (e.g. `validate_url(text)`) returning platform plus a reason: `OK`, `NOT_A_URL`, `UNSUPPORTED_HOST`, `WRONG_SHAPE`.
- `WRONG_SHAPE` examples: YouTube channel/playlist-only/home page with no video; Instagram profile or story link. Decide and document which shapes are accepted (including `/shorts/`, `/live/`, `/reel/`, `/p/`, `/tv/`).
- New translated message per reason (both languages), replacing the single generic "unsupported" where it improves clarity.

**Dependencies:** none beyond the small handler edit.

**Done when:** parametrized pure-function tests cover every shape and reason; all new keys exist in `en` and `fa`; existing tests pass; manual check with five weird inputs on real Telegram.

**Handoff:** `CLAUDE.md` §5 (`manager.py`, translations key list, handler notes), `MODULES.md` module 3.

---

## BRIEF 2C — Failure classification

**Purpose:** turn raw yt-dlp/FFmpeg errors into meaningful categories.

**Scope (may touch):** new `downloader/errors.py`, `downloader/instagram.py`, `downloader/youtube.py`, `tests/test_instagram.py`, `tests/test_youtube.py`, new `tests/test_errors.py`.
**Out of scope:** `bot/*`, `translations.py`, `video_service` (2E/2D consume the categories later).

**Tasks**
- Define a `FailureReason` enum: `UNAVAILABLE` (private/deleted/removed), `AGE_RESTRICTED`, `GEO_BLOCKED`, `BOT_CHECK`, `NETWORK`, `FFMPEG`, `UNKNOWN`.
- Add `classify_error(exc) -> FailureReason` mapping yt-dlp message text (case-insensitive, substring markers) to a reason. Unknown text maps to `UNKNOWN`, never raises.
- Attach the reason to the existing exceptions (`InstagramDownloadError`, `YouTubeExtractionError`, `YouTubeDownloadError`) as an attribute, keeping their types, messages and `from exc` chaining.
- Reuse the existing bot-check markers instead of duplicating them.
- Keep the anonymous-only invariant; the existing no-auth test must still pass.

**Dependencies:** none.

**Done when:** table-driven tests map sample error strings (collect real ones from your logs) to the right reason; unknown text gives `UNKNOWN`; existing downloader tests pass untouched; exceptions still chain.

**Handoff:** `CLAUDE.md` §5, `MODULES.md` modules 4/5 (public interface gains a `reason` attribute; flag this as a contract change to you).

---

## BRIEF 2D — Telegram-side failures and global error handler

**Purpose:** no unexpected exception leaves a user in silence; send failures are told apart.

**Scope (may touch):** `services/video_service.py`, `run.py`, minimal error-handler function in `bot/handlers.py`, related tests.
**Out of scope:** downloaders, keyboards, wording of per-category messages (that is 2E).

**Tasks**
- Per decision 1: let delivery failures carry an optional generic reason while keeping `video_service` free of Telegram/yt-dlp imports.
- Classify send failures (too large, timeout, network, other) in the handler-side sender wrapper. Verify the actual PTB 22.8 exception types in the sandbox first (do not guess; "too large" may surface as a `NetworkError` or `BadRequest` with specific text). Detection only: no pre-send size check (Phase 3).
- Register `application.add_error_handler(...)`: log with traceback (via 2A's logging), then send a translated generic apology if a chat is available. It must never itself raise.
- Re-verify cleanup on every path, including task cancellation and `KEEP_DOWNLOADS`.

**Dependencies:** 2A (logging). Coordinate with 2E on the outcome shape.

**Done when:** a forced exception in each handler produces a logged traceback and one user message; the error handler is tested including the "no chat available" case; all existing `test_video_service.py` cases pass; new cleanup tests cover each failure path.

**Handoff:** `CLAUDE.md` §2/§5, `MODULES.md` modules 6/7 (public interface change: flag it).

---

## BRIEF 2E — UX polish

**Purpose:** clear, specific, bilingual messages.

**Scope (may touch):** `bot/handlers.py`, `bot/keyboards.py`, `services/translations.py`, their tests.
**Out of scope:** downloader internals, `video_service` internals.
**Run alone** (no other active session touching these files).

**Tasks**
- Map 2C `FailureReason` and 2D send reasons to specific translated messages for both platforms (e.g. private video vs. network vs. too large vs. try-later for bot-check).
- Improve status messages where unclear.
- Remove dead key `url.detected_youtube` and its test entries.
- Per decision 2: a simple Retry button for network-type failures only, with its own distinct callback prefix, its own `user_data` key, and expiry/double-tap behaviour matching the YouTube pending-selection design.
- Remove or disable the keyboard on a used/expired menu message where practical.
- Persian wording drafted by the model, flagged for your review.

**Dependencies:** 2B, 2C, 2D merged. Verify `/menu` code is present first (see section 0, item 1).

**Done when:** every `FailureReason` and send reason has a message in both languages (a test enumerates the enum and asserts keys exist); callback prefixes remain non-overlapping (extend the existing prefix test); you have manually verified failure flows on real Telegram in both languages.

**Handoff:** `CLAUDE.md` §2/§5, `MODULES.md` module 6 (new callback prefix/user_data key listed), README.

---

## BRIEF 2F — Test hardening

**Purpose:** close the gaps the other sections leave.

**Scope (may touch):** `tests/` only.
**Out of scope:** production code (report bugs found instead of fixing them silently).

**Tasks**
- Translation parity test: every key has `en` and `fa`, and the `{placeholder}` sets match between languages.
- Run the main flows in both languages (start, language switching via menu, Instagram success/failure, YouTube single/multi/failure).
- Failure-path and cleanup coverage across both platforms, including `KEEP_DOWNLOADS` on and off.
- Confirm no test makes a real network call.

**Dependencies:** best last; can start earlier on existing code.

**Done when:** `pytest tests/ -v` fully green; recount and record the real test total in `CLAUDE.md` §6 (the current text says the total was never recounted).

---

## Final Phase 2 exit check

Mirror roadmap §5: invalid/unsupported/unavailable input handled with specific messages; download, FFmpeg and upload failures handled; cleanup verified after failures; logs diagnosable with no secrets; both languages tested. Then update `PROJECT_ROADMAP.md` §16 to "Phase 2 complete".
