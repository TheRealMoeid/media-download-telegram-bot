# Telegram Video Downloader Bot

A modular Python Telegram bot for downloading videos from supported platforms and sending them back to users.

## Core behavior

- **Instagram:** automatically download the best available quality without intentionally reducing it.
- **YouTube:** inspect the available qualities and let the user choose which quality to download.
- **Language:** on the user's first `/start`, show a **Persian / English** language-selection menu, remember the choice, and allow the user to change it later.

---

## 1. Project Goals

The bot should:

1. Receive a video URL from a Telegram user.
2. Detect the supported platform.
3. Download Instagram videos at the best available quality.
4. Inspect YouTube formats and let the user choose a quality.
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

The bot should automatically select the **best available quality provided by Instagram**, without intentionally lowering the quality.

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

### YouTube

The bot should inspect the actual formats available for the specific video and show the user the available quality choices.

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
Build quality menu
      |
      v
User selects quality
      |
      v
Download selected quality
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

while another might only offer 1080p, 720p, and 480p. Only actually available choices should be displayed.

---

## 4. Recommended Python Stack

| Component | Library / Tool | Purpose |
|---|---|---|
| Telegram bot | `python-telegram-bot` | Telegram Bot API and update handling |
| Video downloading | `yt-dlp` | Extract media information and download supported videos |
| Video processing | `FFmpeg` | Merging, remuxing, conversion, and post-processing |
| Configuration | `python-dotenv` | Load environment variables from `.env` |
| Async HTTP | Built into `python-telegram-bot` | Network communication |

FFmpeg is an external executable, not a normal Python package.

---

## 5. Project Structure

```text
telegram-video-downloader/
|
├── app/
│   ├── __init__.py
│   ├── main.py
│   |
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── handlers.py
│   │   └── keyboards.py
│   |
│   ├── downloader/
│   │   ├── __init__.py
│   │   ├── youtube.py
│   │   ├── instagram.py
│   │   └── manager.py
│   |
│   ├── services/
│   │   ├── __init__.py
│   │   ├── video_service.py
│   │   ├── file_service.py
│   │   └── language_service.py
│   |
│   └── config/
│       ├── __init__.py
│       └── settings.py
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
└── run.py
```

---

## 6. File Responsibilities

| File / Folder | Responsibility |
|---|---|
| `run.py` | Application entry point |
| `app/main.py` | Create/configure/start Telegram application |
| `app/bot/handlers.py` | Telegram commands, URLs, callbacks, user interactions |
| `app/bot/keyboards.py` | Language, settings, and YouTube quality keyboards |
| `app/downloader/youtube.py` | YouTube format inspection and selected-quality downloading |
| `app/downloader/instagram.py` | Instagram best-available-quality downloading |
| `app/downloader/manager.py` | Select appropriate platform downloader |
| `app/services/video_service.py` | Main download workflow/business logic |
| `app/services/file_service.py` | Temporary file management and cleanup |
| `app/services/language_service.py` | Get/set/remember user language |
| `app/config/settings.py` | Configuration and environment variables |
| `downloads/` | Temporary downloaded media |
| `logs/` | Application logs |
| `tests/` | Automated tests |
| `.env` | Secrets such as Telegram bot token |
| `.env.example` | Safe environment-variable template |
| `.gitignore` | Ignore secrets, temporary files, caches, etc. |
| `requirements.txt` | Python dependencies |
| `README.md` | Project documentation |

---

## 7. Language System

Initial supported languages:

| Code | Language |
|---|---|
| `fa` | Persian / فارسی |
| `en` | English |

The language preference should be associated with the Telegram user's ID.

Conceptually:

```text
Telegram User ID
      |
      v
Language Service
      |
      v
User Preference Storage
      |
      v
fa / en
```

The rest of the application should use a small interface such as:

```text
get_language(user_id)
set_language(user_id, language)
```

Handlers should not directly manage the underlying storage.

A centralized translation system should also be used so translated strings are not scattered throughout the codebase.

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

The persistence implementation should be isolated behind `language_service.py`.

This allows the project to start with simple storage and later migrate to a proper database without rewriting the Telegram UI or business logic.

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
          | User Preference   |       | Downloader Manager|
          | Storage           |       +---------+---------+
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

# 10. Phase 1 — MVP

Phase 1 establishes the first complete working vertical slice.

## Phase 1 workflow

```text
FIRST /START
     |
     v
Check language preference
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
Show quality menu              |
      |                         |
      v                         |
User selects quality            |
      |                         |
      +------------+------------+
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

## Phase 1 includes

- Telegram bot initialization.
- `/start`.
- First-time language selection.
- Persian and English.
- Persistent language preference.
- Ability to change language.
- Basic URL validation.
- YouTube detection.
- Instagram detection.
- Instagram best-available-quality download.
- YouTube available-quality extraction.
- YouTube quality-selection menu.
- YouTube selected-quality download.
- FFmpeg integration when required.
- Sending videos to Telegram.
- Temporary file cleanup.
- Basic error handling.

## Not the focus of Phase 1

- Large-scale production queues.
- Distributed workers.
- Admin panel.
- Payment/subscription system.
- Download history.
- Analytics.
- Many additional platforms.
- Advanced media editing.
- Production scaling.

---

## 11. Phase 1 Success Criteria

### Language

- [ ] `/start` detects a first-time user.
- [ ] First-time users receive Persian/English selection.
- [ ] Selected language is persisted.
- [ ] Returning users automatically use their saved language.
- [ ] Users can change language later.
- [ ] Buttons and messages use the selected language.

### Instagram

- [ ] Instagram URL is detected.
- [ ] Best available quality is selected automatically.
- [ ] Quality is not intentionally reduced.
- [ ] Video is sent to the user.
- [ ] Temporary files are removed.

### YouTube

- [ ] YouTube URL is detected.
- [ ] Available qualities are extracted.
- [ ] Only available qualities are displayed.
- [ ] User can select a quality.
- [ ] Selected quality is downloaded.
- [ ] FFmpeg merges streams when required.
- [ ] Video is sent to the user.
- [ ] Temporary files are removed.

### Reliability

- [ ] Invalid URLs are handled.
- [ ] Unsupported URLs are handled.
- [ ] Download errors do not crash the bot.
- [ ] Secrets are loaded from `.env`.
- [ ] Temporary media is excluded from Git.

---

## 12. Development Strategy

Build the project incrementally:

1. **Project foundation** — structure, configuration, dependencies, logging.
2. **Language system** — first-time selection, persistence, and switching.
3. **Telegram URL handling** — receive and validate URLs.
4. **Instagram downloader** — best available quality.
5. **YouTube format extraction** — inspect actual available formats.
6. **YouTube quality menu** — let the user choose.
7. **Selected-quality download** — download according to the choice.
8. **FFmpeg integration** — merge/process streams when necessary.
9. **Telegram upload** — send the result.
10. **Cleanup and error handling** — clean temporary files even after failures.
11. **Testing and refactoring** — verify the complete flow and keep responsibilities separated.

---

## 13. Design Principles

### Separation of concerns

```text
Bot layer          -> Telegram communication
Language service   -> User language preferences
Service layer      -> Application/business logic
Downloader layer   -> Platform-specific media acquisition
File service       -> Filesystem management
Configuration      -> Environment/application settings
```

### Platform-specific quality behavior

```text
Instagram -> Best available automatically
YouTube   -> User chooses from actual available qualities
```

### Don't assume YouTube qualities

Inspect the actual formats for every video.

### Don't intentionally reduce Instagram quality

Select the best suitable quality exposed by the source.

### Keep language logic centralized

Translations and language selection should not be scattered through handlers.

### Abstract preference storage

The application should use language-service methods rather than directly manipulating storage.

### Secrets never belong in source code

Use `.env`.

### Temporary files are disposable

Downloaded media should be deleted after the operation unless a future feature explicitly requires persistent storage.

### Build a vertical slice first

Get the complete user flow working before adding complex infrastructure.

---

## 14. Future Evolution

```text
PHASE 1
Language + Instagram + YouTube
        |
        v
PHASE 2
Better UI + validation + error handling
        |
        v
PHASE 3
Additional platforms + media options
        |
        v
PHASE 4
Queue + workers + concurrency control
        |
        v
PHASE 5
Database + history + user management
        |
        v
Production deployment and scaling
```

The exact phase boundaries can evolve as requirements become clearer.

---

## 15. Final Architecture

```text
+-----------------------------------------------------------+
|                       TELEGRAM USER                       |
+------------------------------+----------------------------+
                               |
                               v
+-----------------------------------------------------------+
|                    BOT / UI LAYER                         |
|             handlers.py / keyboards.py                    |
+-------------------+-------------------+-------------------+
                    |                   |
                    v                   v
        +-------------------+   +-------------------------+
        | LANGUAGE SERVICE  |   |      VIDEO SERVICE      |
        | fa / en           |   | URL -> platform ->     |
        | preferences       |   | download -> processing  |
        +---------+---------+   +------------+------------+
                  |                          |
                  v                          v
        +-------------------+   +-------------------------+
        | Preference        |   | DOWNLOADER MANAGER      |
        | Persistence       |   +------------+------------+
        +-------------------+                |
                                  +----------+----------+
                                  |                     |
                                  v                     v
                           +-------------+       +-------------+
                           |   YouTube   |       |  Instagram  |
                           | User picks  |       | Best quality|
                           | quality     |       | automatically|
                           +------+------+       +------+------+
                                  |                     |
                                  +----------+----------+
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
                                        +---------+
                                        |  File   |
                                        | Service |
                                        +----+----+
                                             |
                                             v
                                        +---------+
                                        |Telegram |
                                        | Upload  |
                                        +----+----+
                                             |
                                             v
                                          Cleanup
```

---

## 16. Current Project Definition

**Project:** Telegram Video Downloader Bot

**Initial languages:** Persian (`fa`) and English (`en`)

**First-time behavior:** Show language-selection menu after `/start`.

**Language persistence:** Remember the selected language per Telegram user.

**Language switching:** Users can change their language whenever they want.

**Instagram policy:** Best available quality automatically.

**YouTube policy:** User chooses from qualities actually available for that video.

**Downloader:** `yt-dlp`

**Media processor:** FFmpeg

**Telegram framework:** `python-telegram-bot`

**Configuration:** `python-dotenv`

**Primary Phase 1 goal:** Build and verify the complete end-to-end experience, including persistent language selection and platform-specific download behavior.
