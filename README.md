# Media Download Telegram Bot

A Python-based Telegram bot designed to receive media download requests and handle video downloading and processing through a modular application architecture.

The project separates Telegram bot interaction, platform-specific downloading, video processing, file management, and configuration into dedicated modules. The current architecture is designed around **YouTube** and **Instagram** downloading.

---

## Features

The project is structured to support the following responsibilities:

- Telegram bot interaction through `python-telegram-bot`.
- Video downloading from YouTube through `yt-dlp`.
- Video downloading from Instagram through `yt-dlp`.
- Selection of the appropriate downloader through a downloader manager.
- Video-processing logic through FFmpeg.
- Temporary media storage in the `downloads/` directory.
- File management and cleanup through a dedicated file service.
- Configuration and environment-variable management through `python-dotenv`.
- Application logging through the `logs/` directory.
- Automated testing through the `tests/` directory.

---

## Architecture

The application follows a layered, modular structure:

```text
Telegram User
      │
      ▼
Telegram Bot
      │
      ▼
app/bot/handlers.py
      │
      ├──────────────► app/bot/keyboards.py
      │
      ▼
app/downloader/manager.py
      │
      ├──────────────► app/downloader/youtube.py
      │
      └──────────────► app/downloader/instagram.py
      │
      ▼
app/services/video_service.py
      │
      ├──────────────► FFmpeg
      │
      └──────────────► app/services/file_service.py
                             │
                             ▼
                        downloads/
      │
      ▼
Telegram Bot
      │
      ▼
User receives processed media
```

The main idea is to keep platform-specific download logic separate from Telegram handling and from general video/file processing.

---

## Project Structure

```text
media-download-telegram-bot/
│
├── run.py
│
├── app/
│   ├── main.py
│   │
│   ├── bot/
│   │   ├── handlers.py
│   │   └── keyboards.py
│   │
│   ├── downloader/
│   │   ├── youtube.py
│   │   ├── instagram.py
│   │   └── manager.py
│   │
│   ├── services/
│   │   ├── video_service.py
│   │   └── file_service.py
│   │
│   └── config/
│       └── settings.py
│
├── downloads/
├── logs/
├── tests/
│
├── .env
├── .env.example
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Python Files

### `run.py`

**Responsibility:** Application entry point.

This file is the top-level entry point used to start the project.

---

### `app/main.py`

**Responsibility:** Initializes and starts the Telegram bot.

This module is responsible for application startup and connecting the main bot components.

---

### `app/bot/handlers.py`

**Responsibility:** Handles Telegram commands and messages.

This is the Telegram interaction layer. It receives user input and connects the Telegram interface to the application's download workflow.

---

### `app/bot/keyboards.py`

**Responsibility:** Provides inline/reply keyboards.

Keyboard definitions are kept separate from message and command handling so the Telegram UI logic remains modular.

---

### `app/downloader/youtube.py`

**Responsibility:** YouTube downloading.

This module contains the YouTube-specific downloading logic.

---

### `app/downloader/instagram.py`

**Responsibility:** Instagram downloading.

This module contains the Instagram-specific downloading logic.

---

### `app/downloader/manager.py`

**Responsibility:** Chooses the appropriate downloader.

The downloader manager acts as the selection layer between the Telegram/application workflow and the platform-specific downloader implementations.

Instead of making the bot directly depend on a specific platform implementation, the manager decides which downloader should be used.

---

### `app/services/video_service.py`

**Responsibility:** Main video-processing logic.

This service coordinates the processing stage after media has been downloaded and uses **FFmpeg** for video-processing operations.

---

### `app/services/file_service.py`

**Responsibility:** File management and cleanup.

This service handles downloaded files and their cleanup, keeping temporary media-management logic separate from downloading and Telegram-specific code.

---

### `app/config/settings.py`

**Responsibility:** Configuration and environment variables.

This module is responsible for application configuration and reading environment-based settings.

The project uses `python-dotenv` for loading configuration from `.env`.

---

## Libraries and Technologies

| Component | Technology | Purpose |
|---|---|---|
| Telegram bot | `python-telegram-bot` | Telegram commands, messages, bot interaction, and keyboards |
| Video downloading | `yt-dlp` | Downloading media from supported platforms such as YouTube and Instagram |
| Video processing | **FFmpeg** | Video-processing operations |
| Configuration | `python-dotenv` | Loading environment variables from `.env` |
| Async HTTP | Built into `python-telegram-bot` | Asynchronous HTTP functionality used by the Telegram bot |
| Language | Python | Main application language |

### `requirements.txt`

Python package dependencies for the project are kept in:

```text
requirements.txt
```

FFmpeg is an external system dependency rather than a Python package.

---

## Component Interaction

The major components interact in the following order:

### 1. Telegram Layer

The user interacts with the bot.

`app/bot/handlers.py` receives the relevant Telegram command or message and starts the application workflow.

### 2. Downloader Manager

The request is passed toward:

```text
app/downloader/manager.py
```

The manager determines which downloader implementation should handle the request.

### 3. Platform Downloader

The selected downloader handles the platform-specific download:

```text
app/downloader/youtube.py
```

or:

```text
app/downloader/instagram.py
```

The project uses `yt-dlp` for video downloading.

### 4. Video Service

After the download stage, the application uses:

```text
app/services/video_service.py
```

for the main video-processing logic.

FFmpeg is used for video processing.

### 5. File Service

File handling and cleanup are delegated to:

```text
app/services/file_service.py
```

Temporary downloaded media is stored under:

```text
downloads/
```

### 6. Response

The processed media can then be handled by the Telegram bot workflow and returned to the user.

---

## Overall Application Workflow

```text
User
  │
  │ Sends a request/message
  ▼
Telegram Bot
  │
  ▼
handlers.py
  │
  ▼
downloader/manager.py
  │
  ├──► youtube.py
  │
  └──► instagram.py
  │
  ▼
yt-dlp
  │
  ▼
downloads/
  │
  ▼
video_service.py
  │
  ▼
FFmpeg
  │
  ▼
file_service.py
  │
  ├──► File management
  └──► Cleanup
  │
  ▼
Telegram Bot
  │
  ▼
User
```

---

## Setup Requirements

Before running the project, make sure the following are available:

- Python
- `pip`
- FFmpeg
- The Python dependencies listed in `requirements.txt`
- A Telegram bot token
- A configured `.env` file

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/TheRealMoeid/media-download-telegram-bot.git
cd media-download-telegram-bot
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it according to your operating system.

On Windows:

```bash
.venv\Scripts\activate
```

On Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg

FFmpeg must be installed separately because it is an external system dependency used for video processing.

Make sure the `ffmpeg` executable is available to the application.

### 5. Configure environment variables

Create a local `.env` file based on `.env.example`.

Example:

```env
BOT_TOKEN=your_telegram_bot_token_here
DOWNLOAD_DIR=downloads/
```

Do **not** commit your real `.env` file or Telegram bot token to GitHub.

---

## Running the Project

Start the application through the project entry point:

```bash
python run.py
```

---

## Environment Configuration

The project keeps environment-specific configuration outside the source code.

### `.env`

Contains local/private configuration values, including secrets such as the Telegram bot token.

This file should remain local and must not be committed to GitHub.

### `.env.example`

Contains an example configuration showing which environment variables the project expects without exposing real secrets.

---

## Temporary Files and Cleanup

Downloaded media is stored in:

```text
downloads/
```

The project also contains a dedicated:

```text
app/services/file_service.py
```

module for file management and cleanup.

The `downloads/` directory should therefore be treated as temporary application data rather than source code.

---

## Logging

Application logs are stored under:

```text
logs/
```

Keeping logging output separate from application source files makes the project easier to operate and debug.

---

## Testing

Automated tests belong in:

```text
tests/
```

Tests should be kept separate from application code and expanded as individual components are implemented.

---

## Development Guidelines

The architecture is intentionally modular.

When modifying the project:

- Keep Telegram-specific logic inside `app/bot/`.
- Keep platform-specific downloading logic inside `app/downloader/`.
- Keep general processing and file-management logic inside `app/services/`.
- Keep configuration and environment-variable handling inside `app/config/`.
- Avoid placing platform-specific logic directly inside Telegram handlers.
- Keep temporary media and logs out of the source-code directories.
- Keep secrets in `.env` and use `.env.example` for shareable configuration documentation.

This separation makes it easier to maintain the project and add additional downloaders or services later without coupling them to the Telegram interface.

---

## Repository

GitHub:

https://github.com/TheRealMoeid/media-download-telegram-bot

---

## License

No specific license information is defined in the current project structure.
