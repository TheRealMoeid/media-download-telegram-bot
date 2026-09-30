# CLAUDE.md — Project Reference

> **Purpose of this file:** This is the shared technical reference for the Telegram Video Downloader Bot project — written for Claude originally, but now the authoritative context document for **any AI model** working on this repo (see `AI_COLLABORATION.md` for why multiple models are now involved and how work is divided between them). It exists to be read at the start of a session to reconstruct full context — architecture, decisions, current state, open issues, and how Moeid and the assisting model work together — without relying on chat history being available. Update this file whenever something material changes (a decision, a completed step, a newly discovered issue). Treat it as more authoritative than any model's memory of past conversations, since this is explicit and versioned; memory can be stale or incomplete.
>
> **If you are a different AI model picking this up for the first time:** also read `AI_COLLABORATION.md` (how multi-model work is coordinated on this project) and `MODULES.md` (the concrete module map — what you can touch independently, what you can't). Reading only this file is not enough once more than one model is active on the project.

---

## 1. What this project is

A modular Python Telegram bot that downloads videos from **YouTube** and **Instagram** and sends them back to the user in Telegram. Supports **Persian (فارسی)** and **English** interfaces, with per-user language preference.

Core product behavior (do not silently change these):

- **Instagram** → auto-download the **best available quality**. No quality menu.
- **YouTube** → inspect the actual formats available for *that specific video* and let the user choose. **Exception:** if only one quality exists, skip the menu, auto-download it, and explicitly tell the user only one quality was available.
- **Language** → first `/start` shows a Persian/English picker; the choice is remembered per Telegram user ID; changeable later. One user's language must never affect another's.

Full rationale and the complete 9-phase plan live in `PROJECT_ROADMAP.md` (repo root, canonical — `docs/PROJECT_ROADMAP.md` is an intentional mirrored copy, root wins on conflict).

---

## 2. Where we are right now

**Current phase: Phase 1 — MVP.**

| Phase 1 area | Status |
|---|---|
| Bot foundation (`/start`, FFmpeg startup check, keyboard, translations) | ✅ Done (Step 4) — **manually verified working against real Telegram**, Sept 4 2026 |
| Language (SQLite persistence, get/has/set) | ✅ Done (Steps 2–3) |
| Config loading (`Settings`, `.env`) | ✅ Done (Step 1) |
| URL handling / platform detection (Step 5) | ✅ Done — **manually verified working against real Telegram**, Sept 17 2026 |
| Instagram downloading (Step 6) | ✅ Downloader implemented and **manually verified against a real Instagram reel**, Sept 21 2026. **Not yet wired into `bot/handlers.py`** — a real Instagram URL still gets the Step 5 placeholder reply today. |
| YouTube downloading + quality menu (Step 7) | ✅ Implementation, quality-selection UI, and pending-selection handling are complete, tested (114 automated tests passing), and now **manually verified end-to-end including successful real downloads**, Sept 27 2026 — see Issue #5 (✅ resolved). Four real downloads across three different videos succeeded (both the merged-format default-client path and the pre-merged `android`-client path), after switching the VLESS exit node from Germany to the Netherlands. Root cause was exit-node IP reputation with YouTube, not `downloader/youtube.py`'s extraction logic or client list, which needed no code changes. |
| Delivery + cleanup (`services/video_service.py`, `services/file_service.py`) | 🔲 Not started — **Track A (Instagram delivery pipeline) is in progress**; Track B (YouTube extraction) closed Sept 27 2026, see below. |

**Current work was split into two independent, parallel tracks** (see `AI_COLLABORATION.md` and `MODULES.md` for the full coordination model); Track B is now closed:

1. **Track A — Instagram delivery pipeline (active).** Build `services/video_service.py` and `services/file_service.py`, wire `downloader/instagram.py` into `bot/handlers.py`, send the resulting file back through Telegram, clean up afterward. This does not depend on YouTube working and can proceed to completion on its own.
2. **Track B — YouTube extraction blocker (Issue #5) — ✅ closed Sept 27 2026.** Diagnosed via manual proxy/exit-node testing (see Issue #5 for the full trail); root cause was the VLESS exit node's IP reputation with YouTube, confirmed independently by a logged-out real browser hitting the identical wall on the flagged IP, and clearing on a different exit node. No changes were made to `downloader/youtube.py` — its fallback-chain logic was correct all along. Next step for YouTube is wiring it into the same delivery pipeline Track A is building for Instagram, once Track A lands.
3. **Track C — YouTube PO-token provider, opportunistic, added Sept 27 2026 (see `MODULES.md` for full detail).** Confined to `downloader/youtube.py`, on its own branch, no deadline. Not a fix for Issue #5 — that's resolved and this addresses a separate, narrower issue (the `ios`/`android` PO-token warnings seen during that investigation). Still anonymous, not the cookie/session-auth option Phase 0 deferred.

These tracks were deliberately chosen so they don't share files in common (see `MODULES.md` for the full dependency map) — they can be run by different AI models/sessions at the same time without coordination overhead beyond each eventually updating this file.

**Note on Step 6 (Instagram):** `downloader/instagram.py` only implements the download step itself (extract + fetch the best-quality file to disk) — it is not yet wired into `bot/handlers.py` or a video/file service. This is exactly what Track A above closes.

---

## 3. Finalized architecture decisions (Phase 0 — do not re-litigate)

| Area | Decision |
|---|---|
| Repo layout | **Flat**, at repo root: `bot/`, `config/`, `downloader/`, `services/`, `tests/`, `run.py`. No `app/` nesting. |
| Language persistence | SQLite, accessed **only** through `services/language_service.py`. No other module touches storage. |
| Translation system | Centralized: stable **message key** + language code → localized string. Storage format = plain Python dict (decided in Phase 1, see §5). |
| FFmpeg | Required external system binary, **not** a Python package. Validated at startup in `run.py` (fail fast), deliberately **not** inside `config/settings.py` — config-loading and dependency-verification are distinct responsibilities. |
| YouTube single-quality edge case | Auto-download + explicit notification, not a one-item menu. |
| Instagram auth | Anonymous `yt-dlp` extraction only in Phase 1. Architecture leaves room for cookie/session auth later. Any future credentials go through `.env`, never hardcoded/echoed to users. |
| Testing | `pytest` + `pytest-asyncio` + stdlib `unittest.mock`. **No real network calls** in the standard suite. Real-download tests (if ever added) belong to a separate integration tier. |
| Logging | stdlib `logging`. Basic in Phase 1, expanded in Phase 2. |
| `yt-dlp` version | Pinned in `requirements.txt`. Upgrades are deliberate and tested, never automatic. |

**The 8 AI Development Rules** (full text in `PROJECT_ROADMAP.md` §15) — the ones I most need to keep front-of-mind:

1. Respect the current phase — don't build Phase 2+ features while in Phase 1.
2. Don't skip dependencies — check what the current step actually needs.
3. Don't over-engineer Phase 1 — no queues/workers/production DB yet.
4. Preserve separation of concerns (no `yt-dlp` in handlers, no DB queries in keyboards, etc.).
5. Platform behavior must stay explicit (Instagram=auto, YouTube=choose) — don't silently change it.
6. Language is a **per-user** preference — never let one user's change bleed into another's.
7. Prefer the smallest change that solves the current phase.
8. Update documentation when architecture materially changes.

---

## 4. Repository structure (current, real)

```text
Downloader Bot/
├── bot/
│   ├── __init__.py
│   ├── handlers.py         # /start, language callback, URL handling, YouTube quality-selection callback, register_handlers()
│   └── keyboards.py        # language_selection_keyboard(), youtube_quality_keyboard()
├── config/
│   ├── __init__.py
│   └── settings.py         # frozen Settings dataclass, Settings.from_env(), module singleton `settings`
├── downloader/
│   ├── __init__.py
│   ├── instagram.py        # download_instagram_video() — anonymous yt-dlp extraction, Step 6, done + verified, not wired
│   ├── youtube.py          # get_available_qualities() / download_youtube_video() — Step 7, done + tested, extraction currently blocked (Issue #5)
│   └── manager.py          # Platform enum + detect_platform() — Step 5, done
├── services/
│   ├── __init__.py
│   ├── language_service.py # get_language / has_saved_language / set_language — SQLite, only module touching it
│   ├── translations.py     # TRANSLATIONS dict + translate(key, lang, **kwargs), incl. url.* and youtube.* keys
│   ├── file_service.py     # empty — Track A (Instagram delivery), in progress
│   └── video_service.py    # empty — Track A (Instagram delivery), in progress
├── tests/
│   ├── __init__.py
│   ├── test_settings.py            # 6 tests
│   ├── test_language_service.py    # 8 tests
│   ├── test_translations.py        # tests for translate(), incl. url.* and youtube.* keys, kwargs formatting — 24 tests
│   ├── test_handlers.py            # unit tests, service layer mocked — 4 tests
│   ├── test_handlers_integration.py# real language_service + tmp SQLite DB, no mocks — 2 tests
│   ├── test_handlers_url.py        # handle_url_message() non-YouTube paths, detect_platform mocked — 3 tests
│   ├── test_handlers_youtube.py    # YouTube quality-selection flow: menus, callbacks, token/expiry/double-tap — 13 tests
│   ├── test_manager.py             # detect_platform(), pure unit tests — 25 tests
│   ├── test_run.py                 # check_ffmpeg() — 2 tests
│   ├── test_instagram.py           # download_instagram_video(), fake yt_dlp.YoutubeDL — 15 tests, Step 6
│   ├── test_youtube.py             # get_available_qualities()/download_youtube_video(), fallback-chain coverage — 27 tests
│   └── test_video_service.py       # empty stub — Track A, in progress
├── downloads/.gitkeep
├── logs/.gitkeep
├── run.py                  # entry point: check_ffmpeg(), builds Application, register_handlers(), run_polling()
├── .env / .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── PROJECT_ROADMAP.md      # canonical
├── AI_COLLABORATION.md     # multi-model coordination framework (why/how work is split, handoff rules)
├── MODULES.md              # concrete module map: ownership, dependencies, integration points
└── docs/PROJECT_ROADMAP.md # intentional mirror
```

---

## 5. Module-by-module implementation notes

### `config/settings.py`
- Frozen `Settings` dataclass. Fields: `bot_token`, `download_dir` (default `"downloads/"`), `db_path` (default `"bot.db"`), `ffmpeg_path` (default `"ffmpeg"`).
- `Settings.from_env(env: Mapping|None = None)` — pure function, defaults to `os.environ` when `env` is not given. This is what makes it testable without real env vars.
- Raises `ConfigurationError` if `BOT_TOKEN` is missing or blank.
- `load_dotenv()` called at module import time.
- Module-level singleton `settings = Settings.from_env()` built at import time — **this means importing `config.settings` anywhere requires `BOT_TOKEN` to already be resolvable** (real `.env` in production, or the env var set explicitly in tests/sandboxes).

### `services/language_service.py`
- Table: `user_language(user_id INTEGER PRIMARY KEY, language TEXT NOT NULL)`.
- Fresh SQLite connection per call; schema applied via `CREATE TABLE IF NOT EXISTS` every connection (idempotent, simple, fine at this scale).
- `SUPPORTED_LANGUAGES = {"fa", "en"}`, default language when unset = `"en"`.
- Public API:
  - `get_language(user_id, db_path=None) -> str` — returns `"en"` if nothing saved.
  - `has_saved_language(user_id, db_path=None) -> bool` — the *only* reliable way to distinguish "never chose" from "chose and it happens to be the default". This is why both functions exist instead of a single `Optional[str]`-returning one.
  - `set_language(user_id, language, db_path=None) -> None` — validates against `SUPPORTED_LANGUAGES`, raises `ValueError` if invalid, upserts via `INSERT ... ON CONFLICT DO UPDATE`.
- `db_path` param on every function is an optional override of `settings.db_path`, purely for testability (tests point it at a tmp file; production code never passes it, relying on the default).
- **This is the only module allowed to touch SQLite directly** (Rule 4).

### `services/translations.py`
- Kept intentionally minimal per explicit instruction: plain dict `TRANSLATIONS: dict[str, dict[str, str]]`, no fallback chains, no JSON/YAML.
- `translate(key, lang, **kwargs) -> str` — raises `KeyError` on unknown key or language (fail loudly, not silently). **Signature changed in Step 7**: now accepts optional keyword arguments, applied via `str.format(**kwargs)`, for the handful of messages that need to embed a runtime value (currently: the YouTube quality label, e.g. `translate("youtube.download_started", "en", quality="1080p")`). Calling without kwargs behaves exactly as before — a template containing `{quality}` is simply returned unformatted if no kwargs are passed, it does not raise. This was anticipated in the original `language_set` design note ("if a third language were ever added this would become a template") — the same mechanism now covers the YouTube messages that need it.
- Keys as of Step 4: `welcome`, `welcome_back`, `choose_language`, `language_set`.
- Keys added in Step 5: `url.detected_youtube`, `url.detected_instagram`, `url.unsupported` — used by `handle_url_message` in `bot/handlers.py`.
- Keys added in Step 7: `youtube.choose_quality`, `youtube.single_quality_auto`, `youtube.download_started`, `youtube.download_complete`, `youtube.selection_expired`, `youtube.extraction_failed`, `youtube.download_failed` — used by the YouTube quality-selection flow in `bot/handlers.py`. The `youtube.single_quality_auto`, `youtube.download_started`, and `youtube.download_complete` keys take the `quality` kwarg described above.
- Dotted key names (`url.*`, `youtube.*`) are just a naming convention (grouping by feature), not a nested-lookup mechanism — `TRANSLATIONS` is still a flat single-level dict keyed by the full string.
- `language_set` is **not parameterized** — it's just two fixed strings, one per language, each already saying "set to [that language]" in that language. This works because there are only two languages; if a third language were ever added this would need to become a template instead of two hardcoded full sentences.
- Handlers must never hardcode user-facing strings — always go through `translate()`.

### `downloader/manager.py` (Step 5)
- `Platform` enum: `YOUTUBE`, `INSTAGRAM`, `UNKNOWN`. Chosen deliberately over a plain string (the project's usual convention for small fixed sets, e.g. `SUPPORTED_LANGUAGES`) because this module is the seam where Phase 4 ("Platform Expansion") will add more platforms later — a closed, typed set is a better fit here than it was for languages.
- `detect_platform(url: str) -> Platform` — pure function, no I/O, no Telegram objects. Validates general URL shape via `urllib.parse.urlparse` (must have `http`/`https` scheme + a netloc), then matches the lowercased hostname against `YOUTUBE_HOSTS` / `INSTAGRAM_HOSTS` domain sets.
- **Never raises.** Malformed input, non-string input, and unrecognized domains all return `Platform.UNKNOWN` — detection "failure" is a normal, expected outcome (users can paste anything), not an error condition.
- `YOUTUBE_HOSTS` covers `youtube.com`, `www.youtube.com`, `m.youtube.com`, `youtu.be`, `www.youtu.be`. `INSTAGRAM_HOSTS` covers `instagram.com`, `www.instagram.com`.
- Scope is intentionally narrow (Rule 3/7): detection only. Does not call `yt-dlp`, does not select/invoke a downloader implementation — `downloader/youtube.py` and `downloader/instagram.py` are the actual downloader implementations, called from `bot/handlers.py`, not from this module.
- 24 unit tests in `tests/test_manager.py` covering all host variants, malformed/empty/non-URL input, non-string input, whitespace handling, and unsupported domains.

### `downloader/instagram.py` (Step 6)
- `download_instagram_video(url, download_dir=None) -> str` — downloads a single Instagram post/reel via yt-dlp's built-in Instagram extractor, **anonymously** (no login/session/cookies - Phase 0 decision), and returns the path to the downloaded file on disk.
- `format="bestvideo+bestaudio/best"` + `merge_output_format="mp4"` is the concrete implementation of "best available quality, never intentionally reduced" (Rule 5): always take the highest-quality video/audio streams yt-dlp can find, merging via FFmpeg when Instagram exposes them separately, falling back to the best single combined stream otherwise.
- `ffmpeg_location` is passed explicitly from `settings.ffmpeg_path` rather than letting yt-dlp fall back to searching `PATH` itself - this keeps it consistent with the same FFmpeg path `run.py`'s startup check already validates, instead of a second, potentially different resolution of "ffmpeg" existing inside yt-dlp's own PATH search.
- `download_dir` is an optional override of `settings.download_dir`, purely for testability - same pattern as `db_path` in `services/language_service.py`. Production code never passes it.
- The actual downloaded filepath is resolved via `info["requested_downloads"][0]["filepath"]` when present (this reflects the true final path after any FFmpeg merge changes the extension), falling back to `ydl.prepare_filename(info)` otherwise.
- All yt-dlp failures (`yt_dlp.utils.DownloadError`) are caught and re-raised as a single `InstagramDownloadError`, chained via `from exc` - callers (eventually `services/video_service.py`) only need to handle one exception type regardless of the underlying yt-dlp failure mode.
- **No cookie/session options are set anywhere in this module** (Phase 1 = anonymous only). A later phase can add optional authentication by extending `_build_ydl_opts()`'s returned dict (e.g. a `cookiefile` key) without changing `download_instagram_video()`'s public signature - this is the "architecture leaves room for auth later" requirement from Phase 0, made concrete.
- **Not yet wired into the bot.** This module only implements the download step in isolation; `bot/handlers.py`, `services/video_service.py`, and `services/file_service.py` do not call it yet, so a real Instagram URL sent to the bot still gets the Step 5 placeholder reply today. **This is exactly what Track A (Instagram delivery pipeline) closes** — see §2 and `MODULES.md`. Unlike the original plan, this no longer waits on YouTube downloading; the two are being worked in parallel (Moeid's explicit decision, given the YouTube extraction blocker in Issue #5).
- **Scope note:** current implementation targets video posts/reels only. Picture posts and carousels are explicitly deferred to a later pass (per Moeid).
- 15 unit tests in `tests/test_instagram.py`, all against a fake `yt_dlp.YoutubeDL` (no real network calls, no real yt-dlp extraction) - covering the happy path, both filepath-resolution branches, download-dir handling (default + explicit override + auto-creation), the exact yt-dlp options passed (format, merge format, ffmpeg path, no-cookies), and error wrapping/chaining.
- **Manually verified Sept 21 2026** against a real public reel (`https://www.instagram.com/reel/DdiDlPkNLjk/`) via a throwaway `manual_test_instagram.py` script (not part of the repo - hits the real network intentionally outside pytest). Successfully downloaded and FFmpeg-merged to `downloads/DdiDlPkNLjk.mp4`; confirmed to play correctly at good quality.

### `downloader/youtube.py` (Step 7)
- `QualityOption` — frozen dataclass: `format_id` (a yt-dlp format *selector* string, e.g. `"137+bestaudio/best"` — opaque to every caller outside this module), `label` (e.g. `"1080p"`, what a button displays), `height` (raw resolution, for sorting/tests only), `client` (which anonymous yt-dlp "player client" produced this option — `None` for yt-dlp's own default, otherwise one of `_FALLBACK_CLIENTS`; opaque to every caller outside this module — see below).
- `get_available_qualities(url) -> list[QualityOption]` — inspects the real formats for `url` (Rule 5: never assume qualities), dedupes by height (keeps the highest-bitrate format at each resolution, falling back to filesize when bitrate is missing), filters out audio-only formats, and appends `+bestaudio/best` to the selector when a format is video-only. Returns highest-to-lowest sorted.
- `download_youtube_video(url, option, download_dir=None) -> str` — **signature takes the whole `QualityOption`, not a bare format string** — downloads `url` using exactly the format and client recorded on `option`, and returns the path to the file on disk. Uses `settings.ffmpeg_path` explicitly, same pattern as Instagram.
- **Anonymous bot-check fallback chain (added after real-world testing hit YouTube's "Sign in to confirm you're not a bot" rejection — see Issue #5):** `get_available_qualities()` tries yt-dlp's own default anonymous behavior first (richest format list when YouTube allows it), and only falls back to a short, fixed, internal list of alternate anonymous "player client" identifiers — `_FALLBACK_CLIENTS = ("android", "ios", "tv")`, tried in that order — if the default is blocked by what looks like YouTube's bot-check, or exposes zero usable video formats. First success wins outright; formats from different clients are never merged; only two or three attempts are ever made (not a general client-enumeration strategy — Rule 3/7).
- **"Same successful context" guarantee:** whichever client succeeded during extraction is recorded on every `QualityOption` returned. `download_youtube_video()` reuses that exact client and makes exactly one attempt — no retry loop on download — so the quality menu and the actual download can never disagree about which anonymous client's view of the video they're based on.
- **Client identifiers never leak outside this module.** `bot/handlers.py` and `bot/keyboards.py` only ever see and pass around whole `QualityOption` objects opaquely — they never read, branch on, or display `.client` or `.format_id`.
- **Anonymous-only, still.** Nothing in this module ever sets `cookiefile`, `cookiesfrombrowser`, `username`, `password`, or any other authentication-related yt-dlp option — this is a checked invariant in the test suite (`test_no_authentication_options_appear_during_a_full_fallback_run`), not just a convention. Any future cookie/session support is a separate, explicit architectural decision for a later phase (Phase 0 decision, unchanged).
- All yt-dlp failures are wrapped: `YouTubeExtractionError` (extraction/inspection failed — either every client attempt failed, or every attempt succeeded but exposed zero usable formats) and `YouTubeDownloadError` (the actual download failed), both chained via `from exc`, mirroring `InstagramDownloadError`'s pattern.
- 27 unit tests in `tests/test_youtube.py`, all against a fake `yt_dlp.YoutubeDL` with a FIFO-scripted sequence of outcomes per attempt (so a single test can express "first attempt blocked, second succeeds"). Covers dedup/normalization logic, default-success, fallback-after-bot-check, fallback-after-empty-formats, stop-at-first-success (never over-tries), full-exhaustion, non-bot-check-errors-don't-retry, the "same client" guarantee on download, and the no-auth-keys regression check.
- **✅ Issue #5 resolved, Sept 27 2026 — no code in this module changed.** The "Sign in to confirm you're not a bot" rejection that blocked every real download attempt (5 videos, 2 countries) turned out to be caused by the VLESS proxy's exit-node IP reputation with YouTube (the Germany exit node in use throughout the original investigation), not by anything in this module's client-fallback logic. Switching the exit node to the Netherlands immediately cleared the rejection on a previously-100%-failing video, confirmed independently by a logged-out real browser hitting the identical wall on the flagged IP and opening normally on the clean one, and then by four successful real downloads across three videos (both the merged default-client path and the pre-merged `android`-client path). See Issue #5 in §8 for the full investigation trail, including the theories that were correctly ruled out along the way (stale yt-dlp pin, missing JS runtime) before the actual cause was found. **Operational implication for future sessions:** if YouTube extraction starts failing again, checking/rotating the VLESS exit node is a reasonable first troubleshooting step, before re-opening a client/method investigation in this file.

### `bot/keyboards.py`
- `LANGUAGE_CALLBACK_PREFIX = "set_lang:"` — callback_data is `f"{LANGUAGE_CALLBACK_PREFIX}{lang_code}"`, e.g. `"set_lang:fa"`.
- `language_selection_keyboard()` returns an `InlineKeyboardMarkup` with one row: 🇮🇷 فارسی / 🇺🇸 English.
- `YOUTUBE_QUALITY_CALLBACK_PREFIX = "yt_quality:"` (Step 7) — callback_data is `f"{YOUTUBE_QUALITY_CALLBACK_PREFIX}{token}:{index}"`, e.g. `"yt_quality:AbC123xy:0"`. **Deliberately carries only a token and a list index — never the URL or a raw yt-dlp format id** — see `bot/handlers.py`'s pending-selection notes below for why.
- `youtube_quality_keyboard(token, options)` (Step 7) — builds one button per row from the real `QualityOption` list `get_available_qualities()` returned for that specific video; never invents or assumes qualities. This function only builds the layout — it doesn't decide what qualities exist (that's `downloader/youtube.py`) and doesn't validate a tap afterwards (that's `bot/handlers.py`).
- **Callback prefixes must stay distinct.** Any future interactive feature needs its own callback-data prefix — `register_handlers()` matches callbacks by regex prefix, in registration order, so two features sharing a prefix (or one being a substring-match of another) would misroute taps. See `MODULES.md` for the full registered-prefix list before adding a new one.

### `bot/handlers.py`
- `start(update, context)`:
  - Returning user (`has_saved_language(user_id)` is `True`) → **single** message: `translate("welcome_back", saved_lang)`. No keyboard.
  - First-time user → **two** messages: (1) `translate("welcome", "en")`, plain, no keyboard; (2) `translate("choose_language", "en")` **with** the language keyboard attached. English is always the default rendering language before any choice exists.
- `handle_language_selection(update, context)`:
  - Parses `lang` out of `callback_query.data` by stripping `LANGUAGE_CALLBACK_PREFIX`.
  - **Order matters:** calls `set_language(user_id, lang)` first, *then* sends the confirmation — confirmation must reflect the just-saved state, not stale state. This is asserted directly in `test_language_selection_saves_before_confirming`.
  - Confirmation is sent as a **new message** (not an edit of the keyboard message) — explicit decision from Moeid.
  - Confirmation text is always `translate("language_set", lang)` using the **newly selected** `lang`, never whatever was active before.
- `handle_url_message(update, context)` (Step 5, extended in Step 7):
  - Registered as a catch-all `MessageHandler(filters.TEXT & ~filters.COMMAND, ...)` — fires on any plain text message that isn't a slash command, so `/start` and other commands are unaffected.
  - Looks up the sender's saved language via `get_language(user_id)`, calls `detect_platform(update.message.text)`. **YouTube URLs are handed off to `_handle_youtube_url()`** for the full quality-selection flow (see below). Instagram and unrecognized links still get the Step 5 placeholder reply (`url.detected_instagram` / `url.unsupported`) via the `_PLATFORM_TRANSLATION_KEYS` dict — Instagram's downloader exists but isn't wired in here yet (that's Track A).
- `_handle_youtube_url(update, context, url, lang)` (Step 7):
  - **Always drops any previously pending YouTube selection for this user first** (`context.user_data.pop(_PENDING_YOUTUBE_KEY, None)`), *before* deciding what to do with the new URL — this is what makes an old menu's button read as "expired" the moment a new YouTube link is sent, regardless of whether the new link turns out to be single- or multi-quality.
  - Calls `get_available_qualities(url)`. Extraction failure or zero usable formats → `translate("youtube.extraction_failed", lang)`.
  - Exactly one quality → auto-download via `_download_youtube_and_report(..., single_quality=True)` and say so explicitly (Rule 5's exception — never a one-item menu).
  - Multiple qualities → generates a fresh `secrets.token_urlsafe(8)` token, stores `{"token": token, "url": url, "options": options}` under `_PENDING_YOUTUBE_KEY` in `context.user_data`, and shows `youtube_quality_keyboard(token, options)`.
- **Pending-selection design (Step 7) — read this before touching any of it:**
  - State lives in `context.user_data` (python-telegram-bot's own per-user dict) under the key `_PENDING_YOUTUBE_KEY = "pending_youtube_selection"` — **at most one pending YouTube selection per user, by construction**. This is in-memory only; it does not survive a bot restart, and that's an accepted Phase 1 tradeoff (no DB, no queue, no custom cache — Rule 3).
  - `handle_youtube_quality_selection(update, context)` parses `token` and `index` out of `callback_query.data`, then: no pending entry at all (bot restarted, or nothing was ever pending) → expired message. Pending entry exists but its token doesn't match (superseded by a newer URL, or a stale button from an old menu) → expired message, **and the still-current pending selection is left untouched** — a stale tap must never clobber a legitimately pending one. Token matches → **the pending entry is deleted immediately, before the download starts** — this is what makes a double-tap on the same button safe: the second update (whether it arrives before or after the first download finishes) always finds nothing pending and gets the expired message instead of triggering a second download.
  - Out-of-range index (shouldn't happen from our own keyboard, but a malformed/tampered `callback_data` is still just an invalid selection, not a crash) → expired message, pending entry also cleared.
- `_download_youtube_and_report(send, url, option, lang, *, single_quality)` (Step 7) — shared by both the auto-download and user-selected paths so the "announce → download → confirm or report failure" sequence exists in exactly one place. `send` is an async callable (`update.message.reply_text` for the auto-download path, a small wrapper around `context.bot.send_message` for the callback path) — this is what lets one function serve both call sites despite python-telegram-bot's `Message.reply_text` and `Bot.send_message` having different signatures. **Stops at download-to-disk** — does not send the file through Telegram or delete it afterward; that's Track A/Track B's eventual delivery wiring, once each platform reaches that point.
- `register_handlers(application)` — registers, in order: `CommandHandler("start", start)`, `CallbackQueryHandler(handle_language_selection, pattern="^set_lang:")`, `CallbackQueryHandler(handle_youtube_quality_selection, pattern="^yt_quality:")`, then `MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url_message)`. Order matters in `python-telegram-bot` — commands and callback buttons are matched before the catch-all text handler gets a chance to see the update. The two callback patterns are non-overlapping prefixes (`set_lang:` vs `yt_quality:`), confirmed not to cross-match.

### `run.py`
- `check_ffmpeg(ffmpeg_path)` — small, standalone, directly-testable function using `shutil.which()`. Raises `RuntimeError` with a clear message if not found. Deliberately **not** a separate `bot/startup.py` module — Moeid's explicit call: not worth a new module for one Phase 1 check.
- `main()` — sets up `logging.basicConfig`, calls `check_ffmpeg(settings.ffmpeg_path)`, builds the `Application` via `Application.builder().token(settings.bot_token).build()`, calls `register_handlers(application)`, then `application.run_polling()`.

---

## 6. Testing conventions established so far

- One test file per module being tested, named `test_<module>.py`.
- Unit tests for handlers **mock the service layer** (`monkeypatch.setattr` on the imported names inside `bot.handlers`) — fast, isolated, no I/O.
- A separate `test_handlers_integration.py` exists specifically to exercise the **real** `language_service` against a **temporary SQLite file** (via `monkeypatch.setattr(language_service_module, "settings", types.SimpleNamespace(db_path=tmp_path_file))`) — no mocking of storage/language logic at all. This was an explicit ask from Moeid after the mocked-only version, to get real DB coverage without touching the production `bot.db` or leaving stray files (pytest's `tmp_path` fixture auto-cleans).
- Async handler tests use `@pytest.mark.asyncio` explicitly on each test (no `pytest.ini`/`asyncio_mode=auto` added — kept minimal, avoided introducing a new config file for something explicit decorators already solve).
- `MagicMock`/`AsyncMock` are used to fake python-telegram-bot's `Update`/`Context` objects rather than constructing real ones — keeps tests fast and decoupled from the library's actual object graphs.
- Pure-function modules (no Telegram/SQLite involved) get straightforward `pytest.mark.parametrize` unit tests with no mocking at all — see `test_manager.py`, which is the simplest test file in the project by design (`detect_platform()` takes a string, returns an enum, nothing to fake).
- yt-dlp-based downloader tests (`test_instagram.py`, `test_youtube.py`) fake the whole `yt_dlp.YoutubeDL` class - no real network calls, no real extraction. `test_youtube.py` extends this pattern with a FIFO-scripted sequence of outcomes per attempt, so a single test can express "first client attempt blocked, second succeeds" — needed once `downloader/youtube.py` gained its multi-attempt fallback chain (Step 7). Real-world correctness is checked separately via a throwaway manual script run once against a live URL, never as part of the pytest suite.
- **Current test count: 114 passing**, confirmed via a full `pytest tests/ -v` run after Step 7 (the YouTube quality-selection flow, including the fallback-chain rewrite). Individually-confirmed counts worth trusting as exact: `test_youtube.py` (27), `test_handlers_youtube.py` (13, new file), `test_translations.py` (24, up from 13 after the Step 7 key additions). The remaining files (`test_settings.py`, `test_language_service.py`, `test_handlers.py`, `test_handlers_integration.py`, `test_handlers_url.py`, `test_manager.py`, `test_run.py`, `test_instagram.py`) were not touched during Step 7 and should be close to their Step 6 figures, but **don't trust a hand-reconstructed per-file sum from this document** — a manual attempt to reconcile all the individual numbers against the confirmed grand total of 114 did not cleanly add up, most likely due to a stale figure for one of the untouched files rather than an actual test-count problem. Run `pytest tests/ -v` (or `--collect-only -q` for a fast count-only pass) to get an exact fresh breakdown rather than trusting this table blindly — same standing advice as after Step 6.

---

## 7. Environment specifics (Moeid's machine)

- **OS:** Windows, PowerShell, Git for Windows with `core.autocrlf=true`.
- **Python:** 3.14.4 (real machine) — sandbox verification during development used 3.12 (close enough for logic verification, but **cannot** catch Python-3.14-specific runtime issues; see Issue #2 below, which only surfaced on the real machine).
- **Venvs:** `.venv` is the active one; a stray `venv` also exists and was flagged for cleanup (not yet done, low priority).
- **FFmpeg:** binary at `D:\Program Files\ffmpeg-2026-08-30_full_build\bin`. Windows PATH issues are a known category of subtle failure here — stale terminal sessions, System vs. User PATH scope, and the ~2047-char PATH length limit are all real suspects if `ffmpeg` mysteriously stops resolving despite correct registry entries.
- **Deno (added during YouTube troubleshooting, see Issue #5):** `deno 2.9.7`, installed via `winget install --id=DenoLand.Deno`, confirmed on PATH. Required by yt-dlp `2025.11.12+` for full YouTube support (an external JS runtime is needed to solve YouTube's JS challenge) — **this is a genuine yt-dlp prerequisite regardless of Issue #5's outcome**, but installing it did **not** resolve the "Sign in to confirm you're not a bot" failure; see Issue #5 for the full story. Same PATH-propagation gotcha as FFmpeg: a `winget install` doesn't take effect in terminal sessions already open at the time — always open a fresh terminal before testing.
- **Local proxy (confirmed root cause of Issue #5, now resolved):** Moeid's traffic (most apps, including this bot's yt-dlp calls) routes through a local VLESS-based proxy (visible in yt-dlp's debug output as `Proxy map: {'http': 'http://127.0.0.1:10808', ...}`) for censorship-circumvention reasons. This is a real, permanent feature of the environment, not a toggle to casually disable for testing — yt-dlp cannot reach YouTube at all with the proxy fully bypassed on this network (confirmed via `proxy=""` testing, which produced connection-refused/timeout errors rather than a clean direct connection). What Issue #5's investigation did establish: the specific **exit node** the VLESS client connects through matters a great deal — the Germany exit node used throughout the original investigation had poor enough IP reputation with YouTube to trigger "sign in to confirm you're not a bot" fairly consistently (confirmed by a logged-out real browser hitting the same wall), while switching to a Netherlands exit node cleared it immediately. Exit-node reputation should now be treated as a normal operational variable for this bot, not a fixed environmental constant — see Issue #5 in §8.
- **Core stack versions actually in use:** see `requirements.txt` — currently `python-telegram-bot==22.8` (bumped from `21.6`, see Issue #2), `yt-dlp==2026.8.19` (**confirmed latest on PyPI** as of the Issue #5 investigation — an upgrade alone will not fix that issue), `python-dotenv==1.2.2`, `pytest==9.0.3`, `pytest-asyncio==1.4.0`.
- **Branching:** work happens on short-lived feature branches (`URL-hanling`, `instagram-download`, etc.) merged into `phase-1`; `main` holds the docs/architecture baseline. Always confirm the actual current branch (`git branch --show-current`) before assuming file state — don't assume a doc or module is missing just because it isn't in the branch expected; check `git log --oneline` for merge history first.
- **Change delivery workflow:** discuss approach in chat → Moeid picks → Claude builds+tests in sandbox → Claude generates a `.patch` via `git diff --cached`, verifies clean apply on a fresh tree → Claude presents the `.patch` → Moeid applies with `git apply`. **Caveat learned the hard way (see Issue #3): this doesn't always work cleanly for edits to existing files** — prefer it for **new files** (low risk, no context-matching needed), fall back to direct instructions/manual edits for small single-line changes to existing files if a patch fails. **For `docs/CLAUDE.md` and `docs/PROJECT_ROADMAP.md` specifically: these are supplied to Claude directly via memory/project context already up to date - Claude must edit that known content directly and hand back the full file, never attempt to fetch or re-derive them from GitHub or assume a different repo layout (see Issue #4).**

---

## 8. Issues encountered & resolutions (chronological, keep appending)

### Issue #1 — `.env.example` had stale markdown fences from copy-paste
- **Symptom:** applying a patch to `.env.example` failed due to CRLF + leftover ` ```env ` fences from a prior copy-paste into the file.
- **Resolution:** excluded `.env.example` from that `git apply`, overwrote it cleanly via PowerShell `Set-Content` instead.
- **Lesson:** CRLF (`core.autocrlf=true`) plus any manual copy-paste history in a file makes it a bad patch target; verify the file's actual current content before trusting a patch context match.

### Issue #2 — `python-telegram-bot==21.6` incompatible with Python 3.14
- **Symptom:** `python run.py` → FFmpeg check passed, `Application.run_polling()` raised `RuntimeError: There is no current event loop in thread 'MainThread'` from inside PTB's `_application.py`, plus a `RuntimeWarning: coroutine 'Updater.start_polling' was never awaited`.
- **Root cause:** PTB 21.6 calls the bare `asyncio.get_event_loop()` internally; Python 3.14 removed the implicit "create one if none exists" fallback that call used to silently rely on (previously just a `DeprecationWarning` in 3.10–3.13), so it now raises outright.
- **Fix:** confirmed (by reading the installed package source) that PTB **v22.4+** wraps this in a try/except specifically for "Python 3.14+ behavior". Verified `python-telegram-bot==22.8` (latest at the time) contains the fix, and confirmed via web search that the breaking changes between v21.6 → v22.8 (removed `filters.CHAT`, `Defaults.disable_web_page_preview`, etc.) don't touch anything this project uses. Full test suite (17 tests in the sandbox at the time) still passed against 22.8.
- **Status:** ✅ Resolved and manually verified working end-to-end on Moeid's real machine (Sept 4, 2026 — `/start` → keyboard → language confirmation, all correct).
- **Lesson:** don't assume a pinned dependency version documented in Phase 0 planning is still valid once the actual runtime (Python 3.14.4, itself a Phase 0 decision) is involved — cross-check compatibility, don't just trust the pin. `requirements.txt` should be treated as something that can need updates even mid-phase when the *runtime* environment surfaces an incompatibility, distinct from casual/undisciplined dependency churn.

### Issue #3 — `git apply` failed on the `requirements.txt` one-line patch
- **Symptom:** `git apply step4-requirements-fix.patch` → `error: patch failed: requirements.txt:1` / `error: requirements.txt: patch does not apply`, despite the patch being verified to apply cleanly against a reconstructed baseline in the sandbox.
- **Root cause:** not fully diagnosed — most likely candidate is a line-ending mismatch between the sandbox-generated patch (LF) and the real file on Moeid's machine (`core.autocrlf=true` environment), causing `git apply`'s strict context-line matching to fail on a single-line diff where there's zero tolerance for near-misses. Never got the exact `git apply` error text with enough detail to fully confirm.
- **Resolution:** abandoned the patch for this specific single-line change; had Moeid edit `requirements.txt` by hand instead (change `21.6` → `22.8` on the one line), then `pip install -r requirements.txt --upgrade`.
- **Lesson / new working rule:** patches are trustworthy for **new files** (git apply just needs to confirm the path doesn't already exist — no context-matching against existing content, so CRLF/whitespace mismatches can't cause a rejection the same way). Patches that **modify a single line or a small existing file** are more fragile on this Windows/CRLF setup and worth defaulting to manual edit instructions instead, at least until the CRLF root cause is actually nailed down. Don't burn more than one troubleshooting round on a trivial single-line patch failure — just give the direct edit.

### Issue #4 — Claude fabricated a root-level `CLAUDE.md`/`PROJECT_ROADMAP.md` layout instead of using the real `docs/` path already known via memory
- **Symptom:** during Step 6 (Instagram downloading), Claude generated a `.patch` targeting `CLAUDE.md` and `PROJECT_ROADMAP.md` at the repo root. `git apply` failed with `error: CLAUDE.md: No such file or directory` because those files only exist at `docs/CLAUDE.md` and `docs/PROJECT_ROADMAP.md` in this repo - there is no root-level copy. This cost multiple back-and-forth rounds (checking `git status`, `git ls-files`, `git branch --show-current`, and eventually a GitHub screenshot) before the real cause was found.
- **Root cause:** Claude had the actual, current, correct content of `docs/CLAUDE.md` and `docs/PROJECT_ROADMAP.md` available directly via memory/project context (Moeid updates these regularly for exactly this reason), but instead of editing that known content in place, Claude reconstructed an assumed repo layout from scratch in a sandbox and invented a root+mirror structure that doesn't match this repo.
- **Resolution:** Claude edited the actual known `docs/` content directly and handed back the complete updated files, with no GitHub lookups, no sandbox repo reconstruction for these two files, and no patch generation against a guessed path.
- **Lesson / new working rule:** when Claude already has current file content via memory or project context, **use that content directly** - treat it as more reliable than anything Claude would otherwise guess, fetch, or reconstruct. Never re-derive a file's repo path or content from GitHub, a sandbox rebuild, or general assumptions about "typical" project layout when the real content is already sitting in context. If there's genuine doubt about whether memory is current, ask Moeid directly ("is this still accurate?") rather than going and fetching it a different way that risks reintroducing exactly this kind of mismatch.

### Issue #5 — YouTube anonymous extraction rejected by every configured client — ✅ RESOLVED Sept 27 2026 (root cause: VLESS exit-node IP reputation)
- **Symptom:** during manual real-Telegram testing of the YouTube quality-selection flow (Step 7), `get_available_qualities()` raised `YouTubeExtractionError`. yt-dlp logged an identical `"Sign in to confirm you're not a bot"` rejection for all four configured anonymous clients (default, `android`, `ios`, `tv`) in `downloader/youtube.py`'s fallback chain. This happened on every real attempt for weeks: 5+ different real videos, tested from 2 different countries (Moeid's own connection, and a friend's in Turkey) — zero successful downloads until resolution.
- **What was ruled out along the way (kept here deliberately, per `AI_COLLABORATION.md` — a ruled-out theory is worth as much to the next session as the one that worked):**
  - **Not a single-video quirk.** A throwaway manual diagnostic script (`manual_test_youtube_fallback.py`) confirmed the identical total rejection on a second, independent real video, ruling out "this one video is flagged" as the explanation.
  - **Not a stale yt-dlp pin.** `yt-dlp==2026.8.19` (the pinned version) was confirmed to already be the latest release on PyPI at the time of checking — upgrading alone would not have helped.
  - **Not a missing JS runtime.** yt-dlp `2025.11.12+` requires an external JavaScript runtime (Deno recommended) to solve YouTube's JS challenge, and its absence produces a very similar-looking failure mode. Deno was installed and verified active (`yt-dlp -v` showed `JS runtimes: deno-2.9.7` and the "no JS runtime" warning gone) — **the exact same bot-check rejection still occurred, unchanged.** This ruled out the missing-JS-runtime theory, though installing Deno was still worth doing regardless (see §7).
  - **Not the client/method choice.** At the time this issue was still open, current yt-dlp documentation was checked and confirmed that `android`/`ios` now require a Proof-of-Origin token they weren't providing — a plausible method-level explanation Moeid had favored over the IP theory. This turned out to be a real, separate quirk (see below) but not the actual cause of the blanket rejection.
- **Root cause, confirmed via a clean diagnostic sequence:**
  1. A standalone script (`manual_test_youtube_proxy.py`, throwaway, not part of the repo) confirmed the proxy genuinely could not be bypassed at the application level on this network — attempts with yt-dlp's `proxy=""` override produced connection-refused/timeout errors, not a working direct connection, ruling out a same-network no-proxy test.
  2. The decisive test instead compared exit nodes directly: opening a previously-100%-failing video (`n3XTZde8ZvQ`) in a **real, logged-out Firefox incognito window** — no yt-dlp, no automation — showed the identical "sign in to confirm you're not a bot" wall on the VLESS client's **Germany** exit node, and opened normally on a **Netherlands** exit node. Same human, same browser, same video, only the exit IP changed.
  3. Re-running the extraction/inspection script against the same video on the Netherlands exit node flipped the result from 100% failure (all four clients) to success on two of them (default: 62 formats; `android`: 5 formats).
  4. Four real end-to-end downloads (not just format inspection) then succeeded on the Netherlands exit node, across three different videos, via both the merged-format default-client path (real FFmpeg merge, confirmed against the real `ffmpeg_path` from `.env`) and the pre-merged `android`-client path. All four files were confirmed playable, not just correctly sized.
- **Conclusion:** the rejection was driven by the VLESS exit node's IP reputation with YouTube (Germany, specifically), not by `downloader/youtube.py`'s client list, fallback logic, or extraction method. **No code in `downloader/youtube.py` was changed to resolve this** — the module's fallback-chain logic was correct throughout the investigation, exactly as earlier entries in this issue already suspected. Two client-specific quirks were also observed and are worth noting but don't block anything, since `get_available_qualities()` stops at the first successful client: `ios` fails with a documented "GVS PO Token" requirement (a real, narrower yt-dlp/YouTube behavior, unrelated to the IP issue), and `tv` failed with an "UNPLAYABLE / page needs to be reloaded" error on one tested video.
- **Operational implication for future sessions:** exit-node reputation is now a known, real variable for this bot's YouTube path, not a fixed environmental constant. **If YouTube extraction starts failing again, checking or rotating the VLESS exit node is the first thing to try**, before re-opening a client/method-level investigation in `downloader/youtube.py`. `manual_test_youtube_proxy.py` and `manual_test_youtube_download.py` (both throwaway, not part of the repo, not committed) are useful starting points for that check if they're still around; otherwise they're simple enough to recreate — inspect-only via `skip_download=True` for a quick check, or a real download via `download=True` plus a real `ffmpeg_location` to confirm end-to-end.
- **Track B (see §2) is closed as of this resolution.**

---

## 9. Working relationship / process notes

- Moeid wants approaches **discussed and compared before any code is written** — always propose options, get his pick, then build.
- He explicitly prefers **minimal, non-over-engineered solutions** at this phase — e.g. rejected creating `bot/startup.py` for a single FFmpeg check, rejected adding fallback complexity to translations, rejected JSON/YAML for translations "at this stage."
- He asked specifically for **real-DB integration test coverage**, not just mocked unit tests, for the language/handlers interaction — worth defaulting to *both* mocked-unit + one real-integration test for future service-layer work, not just mocked tests.
- He self-tests manually against real Telegram (or, for downloaders, via a throwaway script) once patches are applied and wants to be walked through exactly how to do that (token setup, `.env`, FFmpeg check, running, what to expect at each step).
- When something doesn't work, he'll paste raw terminal output/tracebacks — read them carefully for the *actual* failing line before proposing fixes (e.g. Issue #2 required reading the PTB traceback down to the literal `asyncio.get_event_loop()` line, not just pattern-matching on the visible `RuntimeError` text).
- He's willing to do manual/hand edits when patches misbehave rather than insisting on patch purity — don't over-invest in fixing a fragile patch when a two-line manual instruction solves it just as well.
- **He maintains `docs/CLAUDE.md` and `docs/PROJECT_ROADMAP.md` explicitly so Claude always has current project memory without needing to fetch anything** - he is (understandably) frustrated when Claude ignores that and goes to GitHub or reconstructs assumed file layouts instead, since it wastes his time and tokens for no benefit. Default to trusting and editing the content already in context; only go looking elsewhere if Moeid says the context is stale.
- **Moeid now works with multiple AI models in parallel** (he has subscriptions/access to several) and deliberately splits independent work across them rather than serializing everything through one model — see `AI_COLLABORATION.md` for the full framework and `MODULES.md` for the concrete module boundaries this depends on. If you are a model picking up one of the parallel tracks, read both of those files in full before starting, and update this file's relevant sections (§2, §5, §8, §10 as applicable) before considering your piece of work "handed off" — a stale `CLAUDE.md` actively misleads whichever model or session picks up next, which is worse than an honestly incomplete one.

---

## 10. Open items / things to revisit later (not urgent)

- Duplicate venv cleanup (`.venv` vs `venv`) — flagged, not done.
- The CRLF/`git apply` fragility (Issue #3) isn't root-caused. If it recurs on a larger patch, worth actually diagnosing (e.g. `git config core.autocrlf`, comparing `file <path>` line-ending output, or trying `git apply --whitespace=fix`) rather than falling back to manual edits every time.
- ~~Consider whether `PROJECT_ROADMAP.md`'s Phase 0 decisions table should get a note about the `python-telegram-bot` version bump, per Rule 8 (documentation currency).~~ ✅ Done — added to both `PROJECT_ROADMAP.md` and `docs/PROJECT_ROADMAP.md` (Sept 4, 2026).
- ~~No fallback/unrecognized-message handler exists yet~~ — **resolved in Step 5**: `handle_url_message` now replies to any plain text message (URL or not), so this is no longer an open item.
- Instagram picture posts and carousels are not yet supported by `download_instagram_video()` (video-only for now, per Moeid) — explicitly deferred, not a bug.
- ~~Once YouTube downloading exists, the "Delivery" work... becomes the next real milestone - don't start it before YouTube downloading is done, per Rule 7 (both platforms share this pipeline).~~ **Superseded.** Moeid explicitly decided to run Instagram delivery (Track A) and the YouTube extraction fix (Issue #5, Track B) in parallel instead, given Issue #5 is an open-ended external blocker with no known timeline — see §2 and `AI_COLLABORATION.md`. `services/video_service.py`/`services/file_service.py` will initially be built and wired against Instagram only; YouTube gets connected to the same pipeline once Issue #5 is resolved, ideally without needing to duplicate the delivery-layer work (worth designing the pipeline with that in mind, but not over-engineering a generic abstraction for a second platform that isn't ready yet — Rule 3).
- **`python-dotenv could not parse statement starting at line 14`** — this warning has appeared in every single terminal log Moeid has pasted since Step 7 testing began, and is still unresolved. Low priority (the bot starts and runs fine despite it), but worth actually fixing at some point rather than continuing to ignore it. Moeid has declined to paste raw `.env` content (reasonably, since it may contain secrets) and instead offered to run a redacted check (`Get-Content .env | Select-Object -Index 13` piped through a small snippet that only reveals the variable name, not its value) — that redacted output was never actually sent. Whoever picks this up next should re-ask for it specifically, or just ask Moeid to describe what's on that line in general terms (e.g. "is it blank, a comment, a multi-line value, something with unescaped quotes?").
- Possible future operational task: make `_FALLBACK_CLIENTS` in `downloader/youtube.py` configurable (e.g. via `.env`/`Settings`) so a different anonymous client combination can be tried for diagnostics without a code change. Now that Issue #5 (§8) is resolved and confirmed network-level (exit-node IP reputation) rather than client/method-level, this would be a minor convenience at most, not something expected to matter much in practice — deprioritized accordingly. Not started, not scheduled.

---

## 11. Quick-reference: how to pick up work in a new session

1. Read this file fully before touching code - this file (and `PROJECT_ROADMAP.md`) are supplied via memory/project context and should be treated as current; don't re-fetch them from GitHub unless Moeid says this content is stale.
2. **Read `AI_COLLABORATION.md` and `MODULES.md` too, in full, before starting anything** — this project now has more than one AI model working on it in parallel across separate tracks (see §2). Reading only this file is not enough to know what's safe to touch; the module map determines that.
3. Check `PROJECT_ROADMAP.md` §16 ("Current Development Position") to confirm phase.
4. If something about file state is genuinely unclear (e.g. "does this file exist"), ask Moeid directly rather than guessing at repo layout or going to GitHub - see Issue #4.
5. Follow the standard workflow: discuss → Moeid picks → build+test in sandbox → patch (new files) or direct instructions (small edits to existing files) → Moeid applies and manually verifies.
6. Update this file after material progress — new step completed, new decision made, new issue hit and resolved. If you're one of several models working in parallel, this update **is** your handoff — see `AI_COLLABORATION.md` for what a complete handoff needs to include.
