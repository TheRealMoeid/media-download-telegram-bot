# Telegram Video Downloader Bot

A modular Python Telegram bot that downloads videos from **YouTube** and **Instagram** and sends them back to you in Telegram. The interface supports **Persian (فارسی)** and **English**, chosen per user.

> **Status:** Phase 1 (MVP) is functionally complete and has been manually verified against real Telegram for both platforms. The bot is built for **personal use** (a single operator), not as a public service. Several public-bot concerns (size pre-checks, real concurrency, abuse protection) are intentionally deferred to later phases. See [Known limitations](#known-limitations).

---

## Features

- **Instagram:** send a post/reel link and the bot downloads the **best available quality** automatically (no quality menu), then sends the video back.
- **YouTube:** send a link and the bot inspects the formats that actually exist for *that* video and shows a quality menu. Each button shows an **estimated file size** when one can be determined (e.g. `1080p (~85 MB)`).
  - If a video exposes only **one** quality, there is no menu: the bot downloads it automatically and tells you only one quality was available.
- **Languages:** on your first `/start` you pick فارسی or English. The choice is stored per Telegram user ID in SQLite, and one user's choice never affects another's.
- **Cleanup:** every request uses its own temporary directory, which is deleted after the video is sent (or after a failure). Optionally keep downloads with `KEEP_DOWNLOADS=true`.
- **Graceful failures:** extraction, download and upload failures are reported to the user as translated messages instead of crashing the bot.
- **Fail-fast startup:** the bot refuses to start if FFmpeg cannot be found.

### How it behaves

| You send | The bot does |
|---|---|
| `/start` (first time) | Welcome message, then a language picker (🇮🇷 فارسی / 🇺🇸 English) |
| `/start` (returning) | "Welcome back!" in your saved language |
| An Instagram link | Replies "downloading…", downloads at best quality, sends the video |
| A YouTube link (several qualities) | Shows a quality menu; after you tap one, downloads and sends the video, then confirms |
| A YouTube link (one quality) | Auto-downloads, says only one quality was available, sends the video |
| Anything else | Replies that the link isn't supported (YouTube and Instagram only) |

---

## Technology stack

| Component | Tool | Notes |
|---|---|---|
| Runtime | Python 3.14.4 | |
| Telegram | `python-telegram-bot==22.8` | 22.4+ is required on Python 3.14 (21.6 breaks on the event-loop change) |
| Downloading | `yt-dlp==2026.8.19` | Pinned; upgrades are deliberate and tested |
| Media processing | FFmpeg | External binary, **not** a Python package |
| JS runtime | Deno | Required by recent yt-dlp versions for full YouTube support |
| Config | `python-dotenv==1.2.2` | Loads `.env` |
| Storage | SQLite (stdlib) | Language preferences only |
| Tests | `pytest==9.0.3`, `pytest-asyncio==1.4.0` | `unittest.mock` for isolation; no real network calls |
| Logging | stdlib `logging` | Basic in Phase 1 |

---

## Getting started

### Prerequisites

1. **Python 3.14.x**
2. **FFmpeg**, installed and reachable on `PATH` (or point `FFMPEG_PATH` at the executable).
3. **Deno**, installed and on `PATH` (e.g. `winget install --id=DenoLand.Deno` on Windows). Open a **new** terminal afterwards so PATH changes take effect.
4. A **Telegram bot token** from [@BotFather](https://t.me/BotFather).

### Installation

```powershell
git clone <your-repo-url>
cd "Downloader Bot"

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and fill it in. The file must contain plain `KEY=value` lines only (no shell wrapper text).

```env
BOT_TOKEN=your_telegram_bot_token_here
DOWNLOAD_DIR=downloads/
DB_PATH=bot.db
FFMPEG_PATH=ffmpeg
KEEP_DOWNLOADS=false
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | **Yes** | none | Telegram bot token. Startup fails with `ConfigurationError` if missing or blank. |
| `DOWNLOAD_DIR` | No | `downloads/` | Base directory for per-request temporary folders. |
| `DB_PATH` | No | `bot.db` | SQLite file for language preferences. |
| `FFMPEG_PATH` | No | `ffmpeg` | FFmpeg executable name or full path. Validated at startup and passed explicitly to yt-dlp. |
| `KEEP_DOWNLOADS` | No | `false` | Truthy values: `1`, `true`, `yes`, `on` (case-insensitive). Keeps `downloads/req_xxxx/` when the download succeeded, even if sending failed. Nothing deletes kept files automatically. |

> Importing `config.settings` anywhere requires `BOT_TOKEN` to be resolvable, including in scripts and sandboxes.

### Running

```powershell
python run.py
```

The bot checks for FFmpeg, then starts polling. Open your bot in Telegram and send `/start`.

---

## Project structure

```text
Downloader Bot/
├── bot/
│   ├── handlers.py          # /start, language callback, URL routing, Instagram delivery,
│   │                        # YouTube quality flow, shared video sender, handler registration
│   └── keyboards.py         # Language keyboard, YouTube quality keyboard (with size labels)
├── config/
│   └── settings.py          # Frozen Settings dataclass, Settings.from_env(), `settings` singleton
├── downloader/
│   ├── manager.py           # Platform enum + detect_platform() (pure function)
│   ├── instagram.py         # download_instagram_video() - anonymous yt-dlp, best quality
│   └── youtube.py           # get_available_qualities() / download_youtube_video()
├── services/
│   ├── language_service.py  # get/has/set language - the ONLY module touching SQLite
│   ├── translations.py      # TRANSLATIONS dict + translate(key, lang, **kwargs)
│   ├── file_service.py      # Per-request temp dirs + guarded cleanup
│   └── video_service.py     # deliver_video(download_fn, send_fn) -> DeliveryOutcome
├── tests/                   # pytest suite (no real network calls)
├── downloads/ , logs/       # Runtime directories (contents are gitignored)
├── run.py                   # Entry point: FFmpeg check, build Application, run polling
├── requirements.txt
├── .env.example
├── PROJECT_ROADMAP.md       # Canonical phased plan (mirrored at docs/PROJECT_ROADMAP.md)
├── CLAUDE.md                # Technical reference: decisions, state, issues
├── MODULES.md               # Module map and ownership
├── AI_COLLABORATION.md      # Multi-model workflow rules
└── SECURITY.md              # Security policy
```

---

## Architecture

```text
Telegram user
      |
      v
bot/handlers.py  ---- services/language_service.py ---- SQLite
      |          \--- services/translations.py
      |
      v
downloader/manager.py  (detect_platform)
      |
      +-- YouTube   --> downloader/youtube.py   --+
      |                                           |--> yt-dlp --> FFmpeg
      +-- Instagram --> downloader/instagram.py --+
                              |
                              v
               services/video_service.py  deliver_video()
        (temp dir -> download in worker thread -> send -> cleanup)
                              |
                              v
                       Telegram send_video
```

### Key design decisions

- **Thin handlers.** No yt-dlp or detection logic in the Telegram layer. Platform detection lives in `downloader/manager.py`; all SQLite access lives in `services/language_service.py`.
- **Platform-agnostic delivery.** `deliver_video(download_fn, send_fn)` takes a synchronous download function (run via `asyncio.to_thread`) and an async send function, and returns `SENT`, `DOWNLOAD_FAILED` or `SEND_FAILED`. It never raises into the handler. A new platform only needs a new `download_fn`.
- **Per-request temp directories** (`downloads/req_xxxx/`) so concurrent requests for the same video can never share or delete each other's files. Cleanup refuses any path outside the download directory.
- **Anonymous extraction only.** No login, cookies or session state are used for either platform. This is a tested invariant for YouTube. Cookie/session support is a deferred, separate decision.
- **YouTube anonymous client fallback.** `get_available_qualities()` tries yt-dlp's default client first, then falls back through `android → ios → tv` if blocked or if no usable formats are exposed. The successful client is recorded on each `QualityOption` and reused for the actual download (a single attempt, no retry loop), so the menu and the download always agree.
- **Safe quality selection.** Button `callback_data` carries only a random token and a list index, never the URL or a yt-dlp format id. Pending selections live in `context.user_data`. A stale button, a superseded menu or a double-tap all result in an "expired" message rather than a duplicate download.
- **Centralized, per-user translations.** User-facing strings are never hardcoded; handlers call `translate(key, lang, **kwargs)`. A missing key or language raises `KeyError` on purpose.
- **Explicit platform policy.** Instagram = best quality, automatically. YouTube = inspect and let the user choose (except the single-quality case).

---

## Testing

```powershell
pytest tests/ -v
```

- The standard suite performs **no real network calls** and no real downloads. yt-dlp is replaced with fakes, and Telegram objects with mocks.
- Language storage is tested both with mocks and against a real temporary SQLite file.
- Delivery-flow tests run the real `deliver_video()` and `file_service` against `tmp_path`, faking only yt-dlp and `send_video`.
- `tests/conftest.py` forces `keep_downloads=False` so tests never depend on your local `.env`.
- Real-world downloader behavior is checked with throwaway manual scripts against live URLs, never inside pytest.

---

## Known limitations

- **~50 MB upload limit.** Telegram's standard Bot API rejects larger files. There is no pre-send size check; oversized videos fail at send time and the user gets a "couldn't send it" message. The estimated sizes on YouTube buttons exist to help you avoid this. With `KEEP_DOWNLOADS=true` the file stays on disk. A local Bot API server (2 GB limit) is the real fix and is not built.
- **Language switching and a main menu are not implemented.** Only `/start` and the first-time language picker are registered. There is no command or button to change language afterwards, even though the roadmap marks it as done. This is flagged for verification.
- **Sequential processing.** python-telegram-bot handles updates one at a time, so a long download delays other messages. Downloads run in worker threads, so the event loop itself never freezes. Real concurrency control is Phase 3.
- **Pending quality menus are in-memory.** They do not survive a bot restart; an old button simply replies "expired".
- **Instagram: videos and reels only.** Picture posts and carousels are not supported yet.
- **Kept downloads are never auto-cleaned** when `KEEP_DOWNLOADS=true`.
- **Network dependence.** The author's environment routes traffic through a VLESS proxy. YouTube's anonymous "Sign in to confirm you're not a bot" rejection was traced to the proxy **exit node's IP reputation** (a Germany node was blocked; a Netherlands node worked), not to the code. **If YouTube extraction starts failing, try a different exit IP before changing code.**

---

## Roadmap

Development follows a strict 9-phase plan (Phase 0 → Phase 8): architecture → MVP → reliability → resource control → platform expansion → persistence → background jobs → security → deployment. The project is currently in **Phase 1**, with the following open items:

- Verify or implement language switching and a main menu.
- Optional: a YouTube PO-token provider (Track C), a low-priority backlog item for richer `ios`/`android` format lists. It remains anonymous and is not an IP-reputation fix.
- Then Phase 2: reliability, validation and UX polish.

Full details are in [`PROJECT_ROADMAP.md`](./PROJECT_ROADMAP.md).

---

## Documentation

| File | Purpose |
|---|---|
| [`PROJECT_ROADMAP.md`](./PROJECT_ROADMAP.md) | Canonical phased plan and AI development rules |
| [`CLAUDE.md`](./CLAUDE.md) | Technical reference: finalized decisions, per-module notes, issue history |
| [`MODULES.md`](./MODULES.md) | Module map, dependencies and ownership |
| [`AI_COLLABORATION.md`](./AI_COLLABORATION.md) | How parallel multi-model work is coordinated |
| [`SECURITY.md`](./SECURITY.md) | How to report vulnerabilities privately |

---

## Security

Never commit `.env` or your bot token. Report vulnerabilities privately as described in [`SECURITY.md`](./SECURITY.md), not through public issues.