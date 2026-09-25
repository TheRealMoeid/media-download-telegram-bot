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
| 4 | YouTube Downloader | ✅ Implemented, tested — **extraction blocked, Issue #5, open** |
| 5 | Instagram Downloader | ✅ Implemented, tested, verified — not yet wired |
| 6 | Telegram Bot Layer | ✅ Implemented for everything that exists so far |
| 7 | Delivery / Service Layer | 🔲 Not started — in progress now (Track A, Instagram-first) |

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

**What can be developed independently:** Yes — this module's public contract (`QualityOption`, `get_available_qualities()`, `download_youtube_video()`) hasn't needed to change shape since Step 7, and any internal fix to the extraction logic (Issue #5) can happen entirely inside this file without touching anything that calls it.

**What must be shared with other models:**
- The `QualityOption` dataclass shape (`format_id`, `label`, `height`, `client`) — `bot/handlers.py` and `bot/keyboards.py` pass these objects around opaquely (never inspecting `.format_id` or `.client` directly beyond diagnostic logging). **If this shape changes, both of those files need a coordinated update** — this is the one real cross-module coupling point for this module, so a model changing `QualityOption`'s fields must flag it explicitly rather than assume it's isolated.
- **Issue #5, in full** (see `CLAUDE.md` §8) — the current, unresolved extraction blocker. Any model picking up this module must read it before proposing a fix; several plausible fixes have already been tried and ruled out.

**Integration:** `bot/handlers.py` calls `get_available_qualities()` and `download_youtube_video()` directly; no other integration surface.

**Current work here (Track B):** Diagnosing and, if possible, resolving Issue #5. **Scope is confined to this file.** Do not touch `bot/handlers.py`, `bot/keyboards.py`, or `services/*` to chase this issue — none of that layer is implicated in the current failure.

---

## 5. Instagram Downloader

**Responsibilities / scope:** Download the best available quality for a given Instagram URL, anonymously. No quality menu — Instagram's product behavior is auto-select-best, always (Rule 5).

**Files:** `downloader/instagram.py`

**Dependencies:** `config/settings.py` (for `ffmpeg_path`, `download_dir`). Nothing else.

**What can be developed independently:** Yes, fully — same shape and independence as the YouTube downloader module.

**What must be shared with other models:** The `download_instagram_video(url, download_dir=None) -> str` contract and the `InstagramDownloadError` exception type — whichever model builds `services/video_service.py` needs exactly these two things and nothing more from this module.

**Integration:** **Not yet wired to anything.** This is precisely the gap Track A (Delivery / Service Layer, module 7) closes.

---

## 6. Telegram Bot Layer

**Responsibilities / scope:** All Telegram-facing interaction: `/start`, language selection, URL message routing, the full YouTube quality-selection UI and its pending-selection state machine. This is the **integration layer** — it's the one module that legitimately depends on almost every other module, which also makes it the highest-collision-risk module in the project.

**Files:** `bot/handlers.py`, `bot/keyboards.py`

**Dependencies:** `services/language_service.py`, `services/translations.py`, `downloader/manager.py`, `downloader/youtube.py`. (Not yet: `downloader/instagram.py`, `services/video_service.py`, `services/file_service.py` — see Integration below.)

**What can be developed independently:** Only loosely — because this module integrates so much, changes here are the most likely to collide with parallel work elsewhere. New features should extend existing patterns (new translation keys, a new callback prefix, a new pending-state key) rather than restructure what's already working.

**What must be shared with other models:**
- **The full set of registered callback-data prefixes**: `set_lang:` (language selection), `yt_quality:` (YouTube quality selection). Any new interactive feature needs its own distinct prefix — `register_handlers()` matches by regex prefix, so a collision or accidental substring match would misroute taps.
- **The `context.user_data` key namespace**: currently just `_PENDING_YOUTUBE_KEY = "pending_youtube_selection"`. Any future feature needing its own pending state (e.g., an eventual Instagram confirmation step, if one is ever added) needs its own distinct key — reusing this one would silently corrupt the YouTube flow's state.
- The pending-selection design itself (token generation, consume-before-download, stale/double-tap handling) — see `CLAUDE.md` §5's `bot/handlers.py` notes for the full rationale before modifying any of it.

**Integration:** This module *is* the integration point for everything else. **Track A's delivery wiring will add to this file** (calling `download_instagram_video()` and the not-yet-built `services/video_service.py`/`services/file_service.py` from within `handle_url_message()`'s Instagram branch) — this is expected and is exactly what makes this module "owned by Track A" for the duration of that work. **Track B must not touch this file** — see module 4.

---

## 7. Delivery / Service Layer

**Responsibilities / scope:** The shared pipeline both platforms need once a file exists on disk: orchestrate the download → send the file back through Telegram → clean up temporary files → handle failures without crashing. **Not started yet** — this is Track A's current work.

**Files:** `services/video_service.py`, `services/file_service.py` (both currently empty stubs), plus additions to `bot/handlers.py` (module 6) to call into them.

**Dependencies:** `downloader/instagram.py` (module 5) for the first pass; `downloader/youtube.py` (module 4) once Issue #5 is resolved; `bot/handlers.py` (module 6) for wiring.

**What can be developed independently:** The core file-sending and cleanup logic (`services/file_service.py`) can likely be written platform-agnostically from the start — it just needs a file path, regardless of which downloader produced it. `services/video_service.py`'s orchestration logic is where platform-specific branching would live, if any is needed.

**What must be shared with other models:** Whatever public interface `video_service.py` settles on (e.g., something like `deliver_instagram_video(update, context, url)`) needs to be communicated to whoever eventually wires in YouTube, so that integration is additive rather than a rewrite.

**Integration:** Wires into `bot/handlers.py`'s `handle_url_message()`, replacing the current Instagram placeholder branch. **This is being built against Instagram only for now** — worth keeping the design open to a second platform without speculatively over-engineering a generic multi-platform abstraction before YouTube's extraction issue is even resolved (Rule 3).

---

## Shared / high-collision-risk files

These files are touched by more than one module's boundary, or are the kind of shared document two parallel tracks both want to update. Treat any task touching one of these as needing explicit confirmation of scope before starting:

- **`bot/handlers.py`, `bot/keyboards.py`** — the Telegram Bot Layer (module 6). Currently owned by Track A for the duration of the delivery wiring; Track B must not touch these.
- **`CLAUDE.md`, `PROJECT_ROADMAP.md`** — see `AI_COLLABORATION.md` §7 for how documentation-update collisions between parallel tracks are handled.
- **`requirements.txt`** — a dependency bump for one track (e.g., a yt-dlp upgrade attempted as part of Issue #5) is exactly the kind of change that could silently affect the other track (Instagram also depends on yt-dlp). Flag any dependency version change explicitly rather than bumping it as a side effect.
- **`run.py`** — the composition root (builds the `Application`, calls `register_handlers()`, runs the FFmpeg startup check). Low change frequency, but any module needing a new startup-time check (a hypothetical future Deno-presence check, for instance — see `CLAUDE.md` §7) would land here.

---

## Currently active work (update this section as tracks change)

- **Track A — Instagram delivery pipeline.** Owns: module 7 (new), plus additions to module 6. Reads from: module 5 (Instagram downloader, unchanged). Does not touch: module 4 (YouTube downloader).
- **Track B — YouTube extraction fix (Issue #5).** Owns: module 4 only. Does not touch: module 6, module 7, or any other module. See `CLAUDE.md` Issue #5 before starting.

## Open backlog (not started, not currently assigned to either track)

- Making `_FALLBACK_CLIENTS` in `downloader/youtube.py` (module 4) configurable via `.env`/`Settings` for diagnostics, without a code change per attempt. Explicitly **not** to be built reflexively in response to Issue #5 — only worth doing once Issue #5's actual root cause is better understood. See `CLAUDE.md` Issue #5 and §10.
- Extending `run.py`'s startup checks to also verify Deno is present, mirroring the existing FFmpeg check — worth revisiting once Issue #5 is resolved one way or another, since Deno's necessity is confirmed independent of that issue's outcome (see `CLAUDE.md` §7).
