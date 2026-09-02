# Telegram Video Downloader Bot

A modular Python Telegram bot for downloading videos from supported platforms and sending them back to users.

> **Status:** Phase 0 — Planning & Architecture. No implementation exists yet; this document describes the intended design. See [`PROJECT_ROADMAP.md`](./PROJECT_ROADMAP.md) for the full phased development plan and rationale.

## Core behavior

- **Instagram:** automatically download the best available quality without intentionally reducing it.
- **YouTube:** inspect the available qualities for the specific video and let the user choose. If a video only exposes one quality, the bot skips the menu, downloads it automatically, and tells the user only one quality was available.
- **Language:** on the user's first `/start`, show a **Persian / English** language-selection menu, remember the choice per Telegram user, and allow it to be changed later.

---

## 1. Project Goals

The bot should:

1. Receive a video URL from a Telegram user.
2. Detect the supported platform.
3. Download Instagram videos at the best available quality.
4. Inspect YouTube formats and let the user choose a quality (or auto-download when only one exists).
5. Download media using `yt-dlp`.
6. Use FFmpeg when streams need to be merged or processed.
7. Send the resulting video back to the user.
8. Clean up temporary files.
9. Support Persian and English interfaces.
10. Remember each user's language preference.
11. Allow language changes at any time.
12. Provide localized status and error messages.
13. Remain modular for future platforms and features.

---

## 2. User Experience

### First-time language selection

```text
User
  |
  | /start
  v
Check saved language
  |
  +-- Exists ------> Continue in saved language
  |
  +-- Does not exist
          |
          v
   Language Selection
       /       \
    فارسی     English
       \       /
        v     v
      Save selected language
              |
              v
          Main Menu
```

Each Telegram user's preference is independent.

### Changing language

```text
Main Menu
   |
   v
Settings
   |
   v
Language
  /   \
فارسی  English
  \   /
   v
Save new preference
   |
   v
Interface updates
```

---

## 3. Download Behavior

### Instagram

The bot automatically selects the **best available quality provided by Instagram**, without intentionally lowering it.

```text
Instagram URL
      |
      v
Detect Instagram
      |
      v
Instagram Downloader
      |
      v
yt-dlp
      |
      v
Best available quality
      |
      v
FFmpeg if required
      |
      v
Send video
      |
      v
Cleanup
```

The bot cannot create a quality that Instagram did not provide.

Instagram content sometimes requires authentication to extract reliably. Phase 1 uses **anonymous `yt-dlp` extraction only**; the architecture leaves room for optional cookie/session-based authentication in a later phase. Any such credentials would be handled as configuration/secrets (via `.env`), never hardcoded or echoed back to users.

### YouTube

The bot inspects the actual formats available for the specific video and shows the user the available quality choices.

```text
YouTube URL
      |
      v
Detect YouTube
      |
      v
Extract available formats
      |
      v
Only one quality available?
      |
   +--+----------------+
   |                    |
  Yes                   No
   |                    |
   v                    v
Auto-download it   Build quality menu
   |                    |
   |                    v
   |             User selects quality
   |                    |
   +--------+-----------+
            |
            v
   Notify user which quality
   was used (auto or chosen)
            |
            v
       Download
            |
            v
     FFmpeg if required
            |
            v
       Send video
            |
            v
        Cleanup
```

For example, one video might offer:

```text
[ 2160p / 4K ]
[ 1440p      ]
[ 1080p      ]
[ 720p       ]
[ 480p       ]
```

while another might only offer a single quality — in which case the bot downloads it directly and informs the user no choice was necessary. Only actually available choices are ever displayed.

---

## 4. Technology Stack

| Component | Library / Tool | Version / Notes |
|---|---|---|
| Language runtime | Python | 3.14.4 |
| Telegram bot | `python-telegram-bot` | Handles Telegram Bot API and update processing |
| Video downloading | `yt-dlp` | Pinned at `2026.8.19` in `requirements.txt`; extracts media info and downloads supported videos |
| Video processing | FFmpeg | External system binary (not a Python package); merging, remuxing, conversion |
| Configuration | `python-dotenv` | Loads environment variables from `.env` |
| User preference storage | SQLite | Backs `services/language_service.py` starting in Phase 1 |
| Testing | `pytest`, `pytest-asyncio` | `unittest.mock` (stdlib) isolates Telegram/yt-dlp/FFmpeg in tests; no real network calls in the standard suite |
| Logging | stdlib `logging` | Basic in Phase 1, expanded in Phase 2 |
| Async HTTP | Built into `python-telegram-bot` | Network communication |

FFmpeg must be installed and available on the host's `PATH`. The application is expected to validate this at startup and fail fast with a clear error if FFmpeg is missing, rather than discovering the problem mid-download.

---

## 5. Project Structure

This reflects the actual repository layout — a flat structure at the repo root, not nested under an `app/` package.

```text
telegram-video-downloader/
|
├── bot/
│   ├── __init__.py
│   ├── handlers.py
│   └── keyboards.py
|
├── downloader/
│   ├── __init__.py
│   ├── youtube.py
│   ├── instagram.py
│   └── manager.py
|
├── services/
│   ├── __init__.py
│   ├── video_service.py
│   ├── file_service.py
│   └── language_service.py
|
├── config/
│   ├── __init__.py
│   └── settings.py
│
├── downloads/
│   └── .gitkeep
│
├── logs/
│   └── .gitkeep
│
├── tests/
│   ├── __init__.py
│   ├── test_youtube.py
│   ├── test_instagram.py
│   ├── test_video_service.py
│   └── test_language_service.py
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── PROJECT_ROADMAP.md
├── docs/
│   └── PROJECT_ROADMAP.md   # intentional mirrored copy; root file is canonical
└── run.py
```

---

## 6. File Responsibilities

| File / Folder | Responsibility |
|---|---|
| `run.py` | Application entry point |
| `bot/handlers.py` | Telegram commands, URLs, callbacks, user interactions |
| `bot/keyboards.py` | Language, settings, and YouTube quality keyboards |
| `downloader/youtube.py` | YouTube format inspection and selected-/single-quality downloading |
| `downloader/instagram.py` | Instagram best-available-quality downloading |
| `downloader/manager.py` | Selects the appropriate platform downloader |
| `services/video_service.py` | Main download workflow / business logic |
| `services/file_service.py` | Temporary file management and cleanup |
| `services/language_service.py` | Get/set/remember user language; the only module that touches language storage (SQLite in Phase 1) |
| `config/settings.py` | Configuration and environment variables, including FFmpeg-path/startup-check settings |
| `downloads/` | Temporary downloaded media |
| `logs/` | Application logs |
| `tests/` | Automated tests (`pytest` + `pytest-asyncio`) |
| `.env` | Secrets such as the Telegram bot token |
| `.env.example` | Safe environment-variable template |
| `.gitignore` | Ignores secrets, temporary files, caches, etc. |
| `requirements.txt` | Python dependencies (including the pinned `yt-dlp` version) |
| `README.md` | This file |
| `PROJECT_ROADMAP.md` | Canonical, phase-by-phase development plan (mirrored at `docs/PROJECT_ROADMAP.md`) |

---

## 7. Language System

Initial supported languages:

| Code | Language |
|---|---|
| `fa` | Persian / فارسی |
| `en` | English |

The language preference is associated with the Telegram user's ID and stored in SQLite (Phase 1), accessed only through `language_service.py`:

```text
Telegram User ID
      |
      v
Language Service
      |
      v
SQLite (user_id -> language)
      |
      v
fa / en
```

The rest of the application uses a small interface such as:

```text
get_language(user_id)
set_language(user_id, language)
```

Handlers never manage the underlying storage directly.

### Translations

A centralized translation service resolves a stable **message key** plus the user's language code to localized text (e.g., `translate("download.started", lang="fa")`). The underlying storage format for the translated strings themselves — Python dict, JSON, YAML, or otherwise — is an implementation detail decided during Phase 1, not fixed here. What's fixed is the interface: callers ask for a message by key and language, never by embedding raw strings in handlers.

---

## 8. User Preference Persistence

The minimum required logical data is:

```text
user_id -> language
```

Example:

```text
123456789 -> fa
987654321 -> en
```

Phase 1 stores this in **SQLite**. The persistence implementation stays isolated behind `language_service.py`, so the project can later migrate to a different database without rewriting the Telegram UI or business logic.

---

## 9. Complete Project Workflow

```text
                         +------------------+
                         |      USER        |
                         |    Telegram      |
                         +--------+---------+
                                  |
                                  v
                         +------------------+
                         |  BOT HANDLERS    |
                         |   handlers.py    |
                         +--------+---------+
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
          +-------------------+       +-------------------+
          | Language Service  |       |  Video Service    |
          | language_service  |       | video_service.py  |
          +---------+---------+       +---------+---------+
                    |                           |
                    v                           v
          +-------------------+       +-------------------+
          | SQLite            |       | Downloader Manager|
          | (user_id -> lang) |       +---------+---------+
          +-------------------+                 |
                                  +-------------+-------------+
                                  |                           |
                                  v                           v
                         +----------------+          +----------------+
                         |    YouTube     |          |   Instagram    |
                         |  youtube.py    |          |  instagram.py  |
                         +-------+--------+          +-------+--------+
                                 |                           |
                                 +------------+--------------+
                                              |
                                              v
                                         +---------+
                                         | yt-dlp  |
                                         +----+----+
                                              |
                                              v
                                         +---------+
                                         | FFmpeg  |
                                         +----+----+
                                              |
                                              v
                                      +---------------+
                                      | File Service  |
                                      +-------+-------+
                                              |
                                              v
                                      +---------------+
                                      | Telegram Send |
                                      +-------+-------+
                                              |
                                              v
                                            User
                                              |
                                              v
                                           Cleanup
```

---

## 10. Phase 1 — MVP

Phase 1 establishes the first complete working vertical slice. See `PROJECT_ROADMAP.md` for the full phase-by-phase plan; this section only summarizes what Phase 1 covers.

### Phase 1 workflow

```text
FIRST /START
     |
     v
Validate FFmpeg is on PATH (fail fast if missing)
     |
     v
Check language preference (SQLite)
     |
  +--+------------------+
  |                     |
 No preference       Preference exists
  |                     |
  v                     v
Language menu        Main menu
  |
  v
Persian / English
  |
  v
Save preference
  |
  v
Main menu


DOWNLOAD FLOW

User sends URL
      |
      v
Bot receives URL
      |
      v
Detect platform
      |
      +-------------------------+
      |                         |
      v                         v
   YouTube                  Instagram
      |                         |
      v                         v
Extract qualities         Best available
      |                    quality
      v                         |
One quality only?               |
  |         |                   |
 Yes        No                  |
  |         |                   |
  v         v                   |
Auto-DL   Show menu             |
  |         |                   |
  |         v                   |
  |     User selects            |
  |     quality                 |
  |         |                   |
  +----+----+                   |
       |                        |
       +------------+-----------+
                    |
                    v
                Download
                    |
                    v
          FFmpeg if required
                    |
                    v
             Send video
                    |
                    v
               Cleanup
```

### Phase 1 includes

- Telegram bot initialization.
- `/start`.
- Startup FFmpeg availability check.
- First-time language selection.
- Persian and English.
- Persistent language preference (SQLite).
- Ability to change language.
- Basic URL validation.
- YouTube detection.
- Instagram detection.
- Instagram best-available-quality download (anonymous extraction).
- YouTube available-quality extraction.
- YouTube quality-selection menu, with auto-download + notification when only one quality exists.
- YouTube selected-quality download.
- FFmpeg integration when required.
- Sending videos to Telegram.
- Temporary file cleanup.
- Basic error handling and basic logging.

### Not the focus of Phase 1

- Large-scale production queues.
- Distributed workers.
- Admin panel.
- Payment/subscription system.
- Download history.
- Analytics.
- Additional platforms beyond YouTube/Instagram.
- Instagram cookie/session authentication (architecture allows for it later; not implemented yet).
- Advanced media editing.
- Production scaling.

---

## 11. Design Principles

### Separation of concerns

```text
Bot layer          -> Telegram communication
Language service   -> User language preferences (SQLite-backed)
Service layer       -> Application/business logic
Downloader layer     -> Platform-specific media acquisition
File service          -> Filesystem management
Configuration          -> Environment/application settings, FFmpeg check
```

### Platform-specific quality behavior

```text
Instagram -> Best available automatically
YouTube   -> User chooses from actual available qualities
             (auto-downloads + notifies when only one exists)
```

### Don't assume YouTube qualities

Inspect the actual formats for every video.

### Don't intentionally reduce Instagram quality

Select the best suitable quality exposed by the source.

### Keep language logic centralized

Translations and language selection are not scattered through handlers; both go through `language_service.py` and the translation lookup.

### Abstract preference storage

The application uses `language_service.py` methods rather than directly manipulating SQLite elsewhere.

### Secrets never belong in source code

Use `.env`. This includes any future Instagram authentication credentials.

### Temporary files are disposable

Downloaded media is deleted after the operation unless a future feature explicitly requires persistent storage.

### Fail fast on missing dependencies

FFmpeg availability is validated at startup, not discovered mid-download.

### Build a vertical slice first

Get the complete user flow working before adding complex infrastructure.

---

## 12. Further Reading

For the full phased roadmap — including why each phase exists, what to learn, task checklists, and AI development rules for this repository — see [`PROJECT_ROADMAP.md`](./PROJECT_ROADMAP.md).
