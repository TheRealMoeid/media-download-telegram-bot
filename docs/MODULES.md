# MODULES.md — Module Map & Ownership

> **Purpose of this file:** A concrete breakdown of the project into independently-workable parts, for coordinating multiple AI models (see `AI_COLLABORATION.md` for the process this supports). This file changes more often than `AI_COLLABORATION.md` — update it whenever a module's files, dependencies, or status change, the same way `CLAUDE.md` §5 gets updated per module.
>
> **Scope note:** this is 7 modules, not 20. The project is genuinely small enough right now that splitting further (e.g., treating `bot/handlers.py`'s YouTube-specific functions as separate from its language-selection functions) would create coordination overhead with no real benefit — those functions live in one file because they change together and share the same registration/testing patterns. Don't fragment past what's listed here without a concrete reason.

---

## Module list at a glance

| # | Module | Status |
|---|---|---|
| 1 | Configuration | ✅ Done, stable |
| 2 | Language & Translations | ✅ Done, stable |
| 3 | Platform Detection | ✅ Done, stable |
| 4 | YouTube Downloader | ✅ Implemented, tested, and **verified via real successful downloads** — Issue #5 resolved Sept 27 2026 (root cause: VLESS exit-node IP reputation, not this module's code) |
| 5 | Instagram Downloader | ✅ Implemented, tested, verified, and **wired** (Track A, Oct 1 2026) |
| 6 | Telegram Bot Layer | ✅ Implemented — now includes Instagram + YouTube delivery wiring |
| 7 | Delivery / Service Layer | ✅ Done (Track A, Oct 1 2026) — verified against real Telegram for both platforms |

---

## 1. Configuration

**Responsibilities / scope:** Load and validate environment-based configuration. Nothing else — no operational checks (FFmpeg's actual executability lives in `run.py`, deliberately, per `CLAUDE.md` §5).

**Files:** `config/settings.py`

**Dependencies:** None on other project modules. Depends only on `python-dotenv` and stdlib.

**What can be developed independently:** Everything — this is the most independent module in the project.

**What must be shared with other models:** The `Settings` dataclass's field names and types (`bot_token`, `download_dir`, `db_path`, `ffmpeg_path`) — nearly every other module reads at least one of these via the module-level `settings` singleton. **Critical gotcha to communicate to any model touching almost anything in this repo:** importing `config.settings` anywhere requires `BOT_TOKEN` to already be resolvable (real `.env`, or the env var set explicitly) — this affects how sandboxed test runs and diagnostic scripts must be set up, and has bitten past sessions who forgot it.

**Integration:** No integration step needed — it's a leaf dependency everything else imports from.

---

## 2. Language & Translations

**Responsibilities / scope:** Per-user language preference persistence (SQLite) and centralized user-facing string lookup by message key + language code.

**Files:** `services/language_service.py`, `services/translations.py`

**Dependencies:** `config/settings.py` (for `db_path`). Nothing else.

**What can be developed independently:** Yes, fully — no other module's internals need to change for this one to be extended (e.g., adding a third language, or new translation keys).

**What must be shared with other models:**
- The `get_language(user_id, db_path=None)` / `has_saved_language(user_id, db_path=None)` / `set_language(user_id, language, db_path=None)` interface — this is the *only* sanctioned way to touch language storage; no other module may open its own SQLite connection to this data (Rule 4).
- The `translate(key, lang, **kwargs) -> str` interface and the full `TRANSLATIONS` key registry. **Any model adding a new user-facing message anywhere in the project must add it here, in both languages, never hardcode a string in a handler or downloader.** This is a hard rule (Rule 4/6), not a style preference.

**Integration:** Consumers (`bot/handlers.py` today; potentially `services/video_service.py`/`services/file_service.py` once Track A's delivery messages need translated strings) just import and call — no wiring needed beyond adding new keys as required.

---

## 3. Platform Detection

**Responsibilities / scope:** Given a URL, decide which supported platform (if any) it belongs to. Pure function, no I/O, no side effects.

**Files:** `downloader/manager.py`

**Dependencies:** None — pure stdlib (`urllib.parse`, `enum`).

**What can be developed independently:** Yes, completely. This is the seam Phase 4 ("Platform Expansion") will extend with more platforms later — a new platform means adding a new `Platform` enum value and a new host set here, nothing else in this module changes shape.

**What must be shared with other models:** The `Platform` enum values (`YOUTUBE`, `INSTAGRAM`, `UNKNOWN`) and the `detect_platform(url) -> Platform` contract — `bot/handlers.py` branches on this return value directly.

**Integration:** `bot/handlers.py`'s `handle_url_message()` is the only current consumer.

---

## 4. YouTube Downloader

**Responsibilities / scope:** Inspect real YouTube formats for a given URL, normalize/dedupe into presentable quality options, download a selected option to disk. Anonymous yt-dlp only (Phase 0 decision) — see `CLAUDE.md` §3.

**Files:** `downloader/youtube.py`

**Dependencies:** `config/settings.py` (for `ffmpeg_path`, `download_dir`). Nothing else in this project — no knowledge of Telegram, handlers, keyboards, or translations.

**What can be developed independently:** Yes — this module's public contract (`QualityOption`, `get_available_qualities()`, `download_youtube_video()`) hasn't needed to change shape since Step 7, and any internal fix to the extraction logic can happen entirely inside this file without touching anything that calls it.

**What must be shared with other models:**
- The `QualityOption` dataclass shape (`format_id`, `label`, `height`, `client`, `filesize`) — `bot/handlers.py` and `bot/keyboards.py` pass these objects around opaquely (never inspecting `.format_id` or `.client`; `bot/keyboards.py` reads `.label` and `.filesize` for button text only). **`filesize` (estimated bytes, `Optional[int]`, default `None`) was added last on Oct 1 2026 with Moeid's sign-off (Track A)** — existing constructions are unaffected. **If this shape changes again, both of those files need a coordinated update** — this is the one real cross-module coupling point for this module, so a model changing `QualityOption`'s fields must flag it explicitly rather than assume it's isolated. This applies directly to Track C (see below) if it ends up adding a PO-token field to the dataclass.
- **Issue #5, in full (`CLAUDE.md` §8)** — now resolved, but any model touching this module should still read it: it documents which theories were tried and ruled out (stale yt-dlp pin, missing JS runtime, client/method choice) before the real cause (exit-node IP reputation) was found. That history is directly relevant background for Track C below, since a PO-token provider addresses a different, narrower problem than Issue #5 turned out to be.

**Integration:** `bot/handlers.py` calls `get_available_qualities()` and `download_youtube_video()` directly; no other integration surface.

**Current work here (Track C, opportunistic):** see "Currently active work" below.

---

## 5. Instagram Downloader

**Responsibilities / scope:** Download the best available quality for a given Instagram URL, anonymously. No quality menu — Instagram's product behavior is auto-select-best, always (Rule 5).

**Files:** `downloader/instagram.py`

**Dependencies:** `config/settings.py` (for `ffmpeg_path`, `download_dir`). Nothing else.

**What can be developed independently:** Yes, fully — same shape and independence as the YouTube downloader module.

**What must be shared with other models:** The `download_instagram_video(url, download_dir=None) -> str` contract and the `InstagramDownloadError` exception type — whichever model builds `services/video_service.py` needs exactly these two things and nothing more from this module.

**Integration:** Wired (Track A, Oct 1 2026): `bot/handlers.py`'s `_handle_instagram_url()` calls `download_instagram_video(url, request_dir)` through `services/video_service.py`'s `deliver_video()`. The module itself needed no changes.

---

## 6. Telegram Bot Layer

**Responsibilities / scope:** All Telegram-facing interaction: `/start`, language selection, URL message routing, the full YouTube quality-selection UI and its pending-selection state machine. This is the **integration layer** — it's the one module that legitimately depends on almost every other module, which also makes it the highest-collision-risk module in the project.

**Files:** `bot/handlers.py`, `bot/keyboards.py`

**Dependencies:** `services/language_service.py`, `services/translations.py`, `services/video_service.py`, `downloader/manager.py`, `downloader/youtube.py`, `downloader/instagram.py`.

**What can be developed independently:** Only loosely — because this module integrates so much, changes here are the most likely to collide with parallel work elsewhere. New features should extend existing patterns (new translation keys, a new callback prefix, a new pending-state key) rather than restructure what's already working.

**What must be shared with other models:**
- **The full set of registered callback-data prefixes**: `set_lang:` (language selection), `yt_quality:` (YouTube quality selection). Any new interactive feature needs its own distinct prefix — `register_handlers()` matches by regex prefix, so a collision or accidental substring match would misroute taps.
- **The `context.user_data` key namespace**: currently just `_PENDING_YOUTUBE_KEY = "pending_youtube_selection"`. Any future feature needing its own pending state (e.g., an eventual Instagram confirmation step, or a "send vs. don't send" choice) needs its own distinct key — reusing this one would silently corrupt the YouTube flow's state.
- The pending-selection design itself (token generation, consume-before-download, stale/double-tap handling) — see `CLAUDE.md` §5's `bot/handlers.py` notes for the full rationale before modifying any of it.

**Integration:** This module *is* the integration point for everything else. Track A's delivery wiring (Instagram + YouTube through `deliver_video()`, via the shared `_video_sender()`) is now complete and this module is no longer owned by any active track. **Track C (see below) must not touch this file** — same isolation rule Track B followed.

---

## 7. Delivery / Service Layer

**Status:** ✅ Done — Track A, Oct 1 2026.

**Responsibilities / scope:** The shared pipeline both platforms use once a download is requested: create a per-request directory → run the download in a worker thread → send the file → clean up (always, unless `KEEP_DOWNLOADS`) → report an outcome without ever raising. Platform-agnostic; no Telegram, yt-dlp, or translation knowledge.

**Files:** `services/file_service.py`, `services/video_service.py`. (The Telegram-side wiring — `_video_sender()`, `_handle_instagram_url()`, `_download_youtube_and_report()` — lives in `bot/handlers.py`, module 6.)

**Dependencies:** `config/settings.py` (`download_dir`, `keep_downloads`). Nothing else.

**Public interface (what other modules rely on):**
- `deliver_video(download_fn, send_fn) -> DeliveryOutcome` where `download_fn(request_dir: str) -> str` is sync (run via `asyncio.to_thread`) and `send_fn(path: str)` is async. `DeliveryOutcome` is `SENT` / `DOWNLOAD_FAILED` / `SEND_FAILED`.
- `create_request_dir(base_dir=None)` / `cleanup(path, base_dir=None)` in `file_service` (cleanup never raises and refuses paths outside the download dir).

**What can be developed independently:** Yes — a new platform plugs in by passing a different `download_fn`; nothing in this module changes. Phase 2/3 additions (size checks, retries, concurrency limits, timeouts) belong here.

**What must be shared with other models:** `KEEP_DOWNLOADS` semantics (keep the directory when the download succeeded, even if sending failed; always clean up a failed download); that the service catches `Exception` broadly by design; and the decisions recorded in `CLAUDE.md` §2 "Track A decisions" (no size check, no send-vs-don't-send choice, minimal concurrency).

**Integration:** Used by `bot/handlers.py` for both Instagram and YouTube.

## Shared / high-collision-risk files

These files are touched by more than one module's boundary, or are the kind of shared document two parallel tracks both want to update. Treat any task touching one of these as needing explicit confirmation of scope before starting:

- **`bot/handlers.py`, `bot/keyboards.py`** — the Telegram Bot Layer (module 6). No longer owned by an active track now that Track A is complete; Track C must not touch these.
- **`CLAUDE.md`, `PROJECT_ROADMAP.md`** — see `AI_COLLABORATION.md` §7 for how documentation-update collisions between parallel tracks are handled.
- **`requirements.txt`** — a dependency bump for one track is exactly the kind of change that could silently affect another track. Flag any dependency version change explicitly rather than bumping it as a side effect. This applies directly to Track C, which will likely need to add a new package (`bgutil-ytdlp-pot-provider` or similar) — flag it rather than adding it quietly.
- **`run.py`** — the composition root (builds the `Application`, calls `register_handlers()`, runs the FFmpeg startup check). Low change frequency, but any module needing a new startup-time check (a hypothetical future Deno-presence check, for instance, or eventually a PO-token sidecar health check for Track C — see `CLAUDE.md` §7) would land here.

---

## Currently active work (update this section as tracks change)

- **Track A — Delivery pipeline — ✅ complete Oct 1 2026.** Built module 7 (`file_service`, `video_service`), wired Instagram and YouTube through it in module 6, added `KEEP_DOWNLOADS`, and added `QualityOption.filesize` (module 4, with Moeid's sign-off) for estimated sizes on the quality buttons. Decisions and rationale: `CLAUDE.md` §2 "Track A decisions".
- **Track B — YouTube extraction fix (Issue #5) — ✅ closed Sept 27 2026.** Was: module 4 only. Root cause found to be VLESS exit-node IP reputation, not this module's code; no changes were made to `downloader/youtube.py`. Full trail in `CLAUDE.md` §8.
- **Track C — YouTube PO-token provider (`bgutil-ytdlp-pot-provider`), opportunistic — added Sept 27 2026, not started.** Owns: module 4 only, on its own branch, worked on whenever Moeid has time rather than on any deadline. Does not touch: module 6, module 7, or any other module — same isolation rule Track B followed. **Purpose:** not a fix for Issue #5 (that's resolved, and the resolution actually argues against this being an IP-reputation fix — a real, logged-out browser on the flagged exit node produced a genuine token via the real BotGuard challenge and was still blocked, meaning the block was upstream of token validity). Its real value is narrower: it can address two separate, smaller quirks observed during the Issue #5 investigation — the `ios` client's "GVS PO Token" requirement, and `android`'s reduced/SABR-limited format list — by supplying a real Proof-of-Origin token the same way a genuine browser does. **Still anonymous** — no login, no account, no cookies; this is not the cookie/session-auth option Phase 0 explicitly deferred, and should be described that way in any branch/PR to avoid confusion with that separate, still-out-of-scope decision.
  - **Note (Oct 1 2026):** `downloader/youtube.py` changed during Track A — `QualityOption` gained a `filesize` field and the size-estimation helpers were added. Track C should start from the current file, not an older copy.
  - **Architectural note, unresolved and worth deciding before code is written:** this introduces a new external runtime dependency — a local sidecar process (Docker container, or a native Node/Deno HTTP server, e.g. on port 4416) that must be running alongside the bot. This is the same category of decision as installing Deno was (`CLAUDE.md` §7) — infrastructure the bot now depends on, not just a code change. Two open questions for whoever picks this branch up: Docker-based sidecar vs. a native process (Docker is simpler to run but adds a Docker dependency; native avoids that but is more moving parts to keep alive), and how the bot should be configured to find it — likely a new `Settings` field (e.g. `pot_provider_url`), defaulting to unset/disabled, so the bot degrades cleanly to its current behavior if the sidecar isn't running.


## Open backlog (not started, not currently assigned to either track)

- Re-checking whether language *switching* and a main menu actually exist — `PROJECT_ROADMAP.md` ticks them but `bot/handlers.py` registers no command or button for changing language after the first choice. See `CLAUDE.md` §10.
- Files over Telegram's ~50 MB bot limit: local Bot API server, or a size warning on buttons. See `CLAUDE.md` §10.
- Phase 3 concurrency (non-blocking handlers) — PTB currently processes updates sequentially.

- Making `_FALLBACK_CLIENTS` in `downloader/youtube.py` (module 4) configurable via `.env`/`Settings` for diagnostics, without a code change per attempt. Deprioritized now that Issue #5 is resolved and confirmed network-level rather than client/method-level — see `CLAUDE.md` §10.
- Extending `run.py`'s startup checks to also verify Deno is present, mirroring the existing FFmpeg check — still a reasonable idea independent of Issue #5's resolution, since Deno's necessity for YouTube extraction generally is unrelated to the exit-node issue. Not started.
