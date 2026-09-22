# CLAUDE.md — Project Reference

> **Purpose of this file:** This is Claude's own working reference for the Telegram Video Downloader Bot project. It exists to be read at the start of a session to reconstruct full context — architecture, decisions, current state, open issues, and how Moeid and Claude work together — without relying on chat history being available. Update this file whenever something material changes (a decision, a completed step, a newly discovered issue). Treat it as more authoritative than Claude's memory of past conversations, since this is explicit and versioned; memory can be stale or incomplete.

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
| Instagram downloading (Step 6) | ✅ Done — **manually verified working against a real Instagram reel**, Sept 21 2026 (anonymous yt-dlp extraction + FFmpeg merge, confirmed playable output). Currently videos only; picture/carousel support to be added later. |
| YouTube downloading + quality menu | 🔲 Not started — **next up** |
| Delivery + cleanup | 🔲 Not started |

**Immediate next task:** YouTube downloading — implement `downloader/youtube.py` to extract available formats and let the user choose a quality (auto-download + notify when only one quality exists, per Rule 5). Delivery (`services/video_service.py`, `services/file_service.py`, sending the file back through Telegram, cleanup) still follows after both downloaders exist, since it's a shared pipeline for both platforms.

**Note on Step 6:** `downloader/instagram.py` only implements the download step itself (extract + fetch the best-quality file to disk) - it is not yet wired into `bot/handlers.py` or a video/file service, since that wiring is the separate "Delivery" section of `PROJECT_ROADMAP.md`'s Phase 1 task list, not part of "Instagram downloading" itself. Sending a real Instagram URL to the bot today still gets the Step 5 placeholder reply (`url.detected_instagram`), not an actual download - that's expected until the delivery pipeline is built.

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
│   ├── handlers.py         # /start, language-selection callback, register_handlers()
│   └── keyboards.py        # language_selection_keyboard()
├── config/
│   ├── __init__.py
│   └── settings.py         # frozen Settings dataclass, Settings.from_env(), module singleton `settings`
├── downloader/
│   ├── __init__.py
│   ├── instagram.py        # download_instagram_video() — anonymous yt-dlp extraction, Step 6, done + verified
│   ├── youtube.py          # empty — Phase 1 upcoming, next
│   └── manager.py          # Platform enum + detect_platform() — Step 5, done
├── services/
│   ├── __init__.py
│   ├── language_service.py # get_language / has_saved_language / set_language — SQLite, only module touching it
│   ├── translations.py     # TRANSLATIONS dict + translate(key, lang), incl. url.* keys
│   ├── file_service.py     # empty — Phase 1 upcoming
│   └── video_service.py    # empty — Phase 1 upcoming
├── tests/
│   ├── __init__.py
│   ├── test_settings.py            # 6 tests
│   ├── test_language_service.py    # 8 tests
│   ├── test_translations.py        # tests for translate(), incl. url.* keys
│   ├── test_handlers.py            # unit tests, service layer mocked
│   ├── test_handlers_integration.py# real language_service + tmp SQLite DB, no mocks
│   ├── test_handlers_url.py        # handle_url_message(), detect_platform mocked — 4 tests
│   ├── test_manager.py             # detect_platform(), pure unit tests — 25 tests
│   ├── test_run.py                 # check_ffmpeg()
│   ├── test_instagram.py           # download_instagram_video(), fake yt_dlp.YoutubeDL — 15 tests, Step 6
│   └── test_video_service.py       # empty stub
├── downloads/.gitkeep
├── logs/.gitkeep
├── run.py                  # entry point: check_ffmpeg(), builds Application, register_handlers(), run_polling()
├── .env / .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── PROJECT_ROADMAP.md      # canonical
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
- `translate(key, lang) -> str` — raises `KeyError` on unknown key or language (fail loudly, not silently).
- Keys as of Step 4: `welcome`, `welcome_back`, `choose_language`, `language_set`.
- Keys added in Step 5: `url.detected_youtube`, `url.detected_instagram`, `url.unsupported` — used by `handle_url_message` in `bot/handlers.py`. Dotted key names are just a naming convention (grouping by feature), not a nested-lookup mechanism — `TRANSLATIONS` is still a flat single-level dict keyed by the full string.
- `language_set` is **not parameterized** — it's just two fixed strings, one per language, each already saying "set to [that language]" in that language. This works because there are only two languages; if a third language were ever added this would need to become a template instead of two hardcoded full sentences.
- Handlers must never hardcode user-facing strings — always go through `translate()`.

### `downloader/manager.py` (Step 5)
- `Platform` enum: `YOUTUBE`, `INSTAGRAM`, `UNKNOWN`. Chosen deliberately over a plain string (the project's usual convention for small fixed sets, e.g. `SUPPORTED_LANGUAGES`) because this module is the seam where Phase 4 ("Platform Expansion") will add more platforms later — a closed, typed set is a better fit here than it was for languages.
- `detect_platform(url: str) -> Platform` — pure function, no I/O, no Telegram objects. Validates general URL shape via `urllib.parse.urlparse` (must have `http`/`https` scheme + a netloc), then matches the lowercased hostname against `YOUTUBE_HOSTS` / `INSTAGRAM_HOSTS` domain sets.
- **Never raises.** Malformed input, non-string input, and unrecognized domains all return `Platform.UNKNOWN` — detection "failure" is a normal, expected outcome (users can paste anything), not an error condition.
- `YOUTUBE_HOSTS` covers `youtube.com`, `www.youtube.com`, `m.youtube.com`, `youtu.be`, `www.youtu.be`. `INSTAGRAM_HOSTS` covers `instagram.com`, `www.instagram.com`.
- Scope is intentionally narrow (Rule 3/7): detection only. Does not call `yt-dlp`, does not select/invoke a downloader implementation — `downloader/youtube.py` and `downloader/instagram.py` are still empty stubs. That wiring is later Phase 1 work.
- 24 unit tests in `tests/test_manager.py` covering all host variants, malformed/empty/non-URL input, non-string input, whitespace handling, and unsupported domains.

### `downloader/instagram.py` (Step 6)
- `download_instagram_video(url, download_dir=None) -> str` — downloads a single Instagram post/reel via yt-dlp's built-in Instagram extractor, **anonymously** (no login/session/cookies - Phase 0 decision), and returns the path to the downloaded file on disk.
- `format="bestvideo+bestaudio/best"` + `merge_output_format="mp4"` is the concrete implementation of "best available quality, never intentionally reduced" (Rule 5): always take the highest-quality video/audio streams yt-dlp can find, merging via FFmpeg when Instagram exposes them separately, falling back to the best single combined stream otherwise.
- `ffmpeg_location` is passed explicitly from `settings.ffmpeg_path` rather than letting yt-dlp fall back to searching `PATH` itself - this keeps it consistent with the same FFmpeg path `run.py`'s startup check already validates, instead of a second, potentially different resolution of "ffmpeg" existing inside yt-dlp's own PATH search.
- `download_dir` is an optional override of `settings.download_dir`, purely for testability - same pattern as `db_path` in `services/language_service.py`. Production code never passes it.
- The actual downloaded filepath is resolved via `info["requested_downloads"][0]["filepath"]` when present (this reflects the true final path after any FFmpeg merge changes the extension), falling back to `ydl.prepare_filename(info)` otherwise.
- All yt-dlp failures (`yt_dlp.utils.DownloadError`) are caught and re-raised as a single `InstagramDownloadError`, chained via `from exc` - callers (eventually `services/video_service.py`) only need to handle one exception type regardless of the underlying yt-dlp failure mode.
- **No cookie/session options are set anywhere in this module** (Phase 1 = anonymous only). A later phase can add optional authentication by extending `_build_ydl_opts()`'s returned dict (e.g. a `cookiefile` key) without changing `download_instagram_video()`'s public signature - this is the "architecture leaves room for auth later" requirement from Phase 0, made concrete.
- **Not yet wired into the bot.** This module only implements the download step in isolation; `bot/handlers.py`, `services/video_service.py`, and `services/file_service.py` are unchanged, so a real Instagram URL sent to the bot still gets the Step 5 placeholder reply today. Wiring this in is part of the separate "Delivery" work, which naturally comes after both downloaders (Instagram + YouTube) exist.
- **Scope note:** current implementation targets video posts/reels only. Picture posts and carousels are explicitly deferred to a later pass (per Moeid).
- 15 unit tests in `tests/test_instagram.py`, all against a fake `yt_dlp.YoutubeDL` (no real network calls, no real yt-dlp extraction) - covering the happy path, both filepath-resolution branches, download-dir handling (default + explicit override + auto-creation), the exact yt-dlp options passed (format, merge format, ffmpeg path, no-cookies), and error wrapping/chaining.
- **Manually verified Sept 21 2026** against a real public reel (`https://www.instagram.com/reel/DdiDlPkNLjk/`) via a throwaway `manual_test_instagram.py` script (not part of the repo - hits the real network intentionally outside pytest). Successfully downloaded and FFmpeg-merged to `downloads/DdiDlPkNLjk.mp4`; confirmed to play correctly at good quality.

### `bot/keyboards.py`
- `LANGUAGE_CALLBACK_PREFIX = "set_lang:"` — callback_data is `f"{LANGUAGE_CALLBACK_PREFIX}{lang_code}"`, e.g. `"set_lang:fa"`.
- `language_selection_keyboard()` returns an `InlineKeyboardMarkup` with one row: 🇮🇷 فارسی / 🇺🇸 English.

### `bot/handlers.py`
- `start(update, context)`:
  - Returning user (`has_saved_language(user_id)` is `True`) → **single** message: `translate("welcome_back", saved_lang)`. No keyboard.
  - First-time user → **two** messages: (1) `translate("welcome", "en")`, plain, no keyboard; (2) `translate("choose_language", "en")` **with** the language keyboard attached. English is always the default rendering language before any choice exists.
- `handle_language_selection(update, context)`:
  - Parses `lang` out of `callback_query.data` by stripping `LANGUAGE_CALLBACK_PREFIX`.
  - **Order matters:** calls `set_language(user_id, lang)` first, *then* sends the confirmation — confirmation must reflect the just-saved state, not stale state. This is asserted directly in `test_language_selection_saves_before_confirming`.
  - Confirmation is sent as a **new message** (not an edit of the keyboard message) — explicit decision from Moeid.
  - Confirmation text is always `translate("language_set", lang)` using the **newly selected** `lang`, never whatever was active before.
- `handle_url_message(update, context)` (Step 5):
  - Registered as a catch-all `MessageHandler(filters.TEXT & ~filters.COMMAND, ...)` — fires on any plain text message that isn't a slash command, so `/start` and other commands are unaffected.
  - Looks up the sender's saved language via `get_language(user_id)`, calls `detect_platform(update.message.text)` from `downloader/manager.py`, and replies with the matching translation (`url.detected_youtube` / `url.detected_instagram` / `url.unsupported`) via a small `_PLATFORM_TRANSLATION_KEYS` dict mapping `Platform` → translation key.
  - Does **not** download anything — `downloader/youtube.py` is still empty, and even though `downloader/instagram.py` now works standalone (Step 6), it is not called from here yet. This only closes the detection loop end-to-end (user gets a clear reply instead of silence); actual wiring to downloading is later Phase 1 "Delivery" work.
- `register_handlers(application)` — registers, in order: `CommandHandler("start", start)`, `CallbackQueryHandler(handle_language_selection, pattern=f"^{LANGUAGE_CALLBACK_PREFIX}")`, then `MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url_message)`. Order matters in `python-telegram-bot` — commands and callback buttons are matched before the catch-all text handler gets a chance to see the update.

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
- yt-dlp-based downloader tests (see `test_instagram.py`) fake the whole `yt_dlp.YoutubeDL` class - no real network calls, no real extraction. Real-world correctness is checked separately via a throwaway manual script run once against a live URL, never as part of the pytest suite.
- **Current test count: 79 passing**, confirmed via a full sandbox rebuild + `pytest tests/ -v` run through Step 6. Breakdown: `test_settings.py` (6), `test_language_service.py` (8), `test_translations.py` (13, parametrized over 7 keys plus 6 direct tests), `test_handlers.py` (4), `test_handlers_integration.py` (2), `test_run.py` (2), `test_manager.py` (25, parametrized), `test_handlers_url.py` (4), `test_instagram.py` (15, Step 6), plus empty stub files (`test_video_service.py`, `test_youtube.py`) contributing 0. Treat this number as current as of Step 6; recount rather than trust it blindly once more steps land.

---

## 7. Environment specifics (Moeid's machine)

- **OS:** Windows, PowerShell, Git for Windows with `core.autocrlf=true`.
- **Python:** 3.14.4 (real machine) — sandbox verification during development used 3.12 (close enough for logic verification, but **cannot** catch Python-3.14-specific runtime issues; see Issue #2 below, which only surfaced on the real machine).
- **Venvs:** `.venv` is the active one; a stray `venv` also exists and was flagged for cleanup (not yet done, low priority).
- **FFmpeg:** binary at `D:\Program Files\ffmpeg-2026-08-30_full_build\bin`. Windows PATH issues are a known category of subtle failure here — stale terminal sessions, System vs. User PATH scope, and the ~2047-char PATH length limit are all real suspects if `ffmpeg` mysteriously stops resolving despite correct registry entries.
- **Core stack versions actually in use:** see `requirements.txt` — currently `python-telegram-bot==22.8` (bumped from `21.6`, see Issue #2), `yt-dlp==2026.8.19`, `python-dotenv==1.2.2`, `pytest==9.0.3`, `pytest-asyncio==1.4.0`.
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

---

## 9. Working relationship / process notes

- Moeid wants approaches **discussed and compared before any code is written** — always propose options, get his pick, then build.
- He explicitly prefers **minimal, non-over-engineered solutions** at this phase — e.g. rejected creating `bot/startup.py` for a single FFmpeg check, rejected adding fallback complexity to translations, rejected JSON/YAML for translations "at this stage."
- He asked specifically for **real-DB integration test coverage**, not just mocked unit tests, for the language/handlers interaction — worth defaulting to *both* mocked-unit + one real-integration test for future service-layer work, not just mocked tests.
- He self-tests manually against real Telegram (or, for downloaders, via a throwaway script) once patches are applied and wants to be walked through exactly how to do that (token setup, `.env`, FFmpeg check, running, what to expect at each step).
- When something doesn't work, he'll paste raw terminal output/tracebacks — read them carefully for the *actual* failing line before proposing fixes (e.g. Issue #2 required reading the PTB traceback down to the literal `asyncio.get_event_loop()` line, not just pattern-matching on the visible `RuntimeError` text).
- He's willing to do manual/hand edits when patches misbehave rather than insisting on patch purity — don't over-invest in fixing a fragile patch when a two-line manual instruction solves it just as well.
- **He maintains `docs/CLAUDE.md` and `docs/PROJECT_ROADMAP.md` explicitly so Claude always has current project memory without needing to fetch anything** - he is (understandably) frustrated when Claude ignores that and goes to GitHub or reconstructs assumed file layouts instead, since it wastes his time and tokens for no benefit. Default to trusting and editing the content already in context; only go looking elsewhere if Moeid says the context is stale.

---

## 10. Open items / things to revisit later (not urgent)

- Duplicate venv cleanup (`.venv` vs `venv`) — flagged, not done.
- The CRLF/`git apply` fragility (Issue #3) isn't root-caused. If it recurs on a larger patch, worth actually diagnosing (e.g. `git config core.autocrlf`, comparing `file <path>` line-ending output, or trying `git apply --whitespace=fix`) rather than falling back to manual edits every time.
- ~~Consider whether `PROJECT_ROADMAP.md`'s Phase 0 decisions table should get a note about the `python-telegram-bot` version bump, per Rule 8 (documentation currency).~~ ✅ Done — added to both `PROJECT_ROADMAP.md` and `docs/PROJECT_ROADMAP.md` (Sept 4, 2026).
- ~~No fallback/unrecognized-message handler exists yet~~ — **resolved in Step 5**: `handle_url_message` now replies to any plain text message (URL or not), so this is no longer an open item.
- Instagram picture posts and carousels are not yet supported by `download_instagram_video()` (video-only for now, per Moeid) — explicitly deferred, not a bug.
- Once YouTube downloading exists, the "Delivery" work (video_service.py, file_service.py, wiring both downloaders into bot/handlers.py, sending files via Telegram, cleanup) becomes the next real milestone - don't start it before YouTube downloading is done, per Rule 7 (both platforms share this pipeline).

---

## 11. Quick-reference: how to pick up work in a new session

1. Read this file fully before touching code - this file (and `PROJECT_ROADMAP.md`) are supplied via memory/project context and should be treated as current; don't re-fetch them from GitHub unless Moeid says this content is stale.
2. Check `PROJECT_ROADMAP.md` §16 ("Current Development Position") to confirm phase.
3. If something about file state is genuinely unclear (e.g. "does this file exist"), ask Moeid directly rather than guessing at repo layout or going to GitHub - see Issue #4.
4. Follow the standard workflow: discuss → Moeid picks → build+test in sandbox → patch (new files) or direct instructions (small edits to existing files) → Moeid applies and manually verifies.
5. Update this file after material progress — new step completed, new decision made, new issue hit and resolved.
