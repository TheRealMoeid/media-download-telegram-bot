# Telegram Video Downloader Bot — Complete Project Roadmap

> **Document type:** Planning and roadmap  
> **Purpose:** Define the complete development path of the Telegram Video Downloader Bot so that the developer and AI assistants always understand what each phase is trying to accomplish, why it exists, what must be learned, and what must be completed before moving forward.
>
> **Important:** This document intentionally contains **no implementation code**. It is a project-planning document.
>
> **Canonical copy:** This file (`PROJECT_ROADMAP.md`, repository root) is the canonical version. A mirrored copy exists at `docs/PROJECT_ROADMAP.md` intentionally (e.g., for docs-site tooling). When the two differ, this root copy is authoritative, and the `docs/` copy should be updated to match it.

---

# 1. Project Vision

The project is a Telegram bot that allows users to send supported video URLs and receive the downloaded video directly in Telegram.

The core product behavior is:

- **Instagram:** automatically download the best available quality without intentionally reducing it.
- **YouTube:** inspect the formats available for the specific video and let the user choose the desired quality.
- **Languages:** support Persian and English.
- **First-time users:** choose their language after starting the bot.
- **Returning users:** continue using their saved language automatically.
- **Language switching:** users can change their language whenever they want.
- **Temporary media:** downloaded files are processed, sent to Telegram, and cleaned up.
- **Architecture:** platform-specific download logic is separated from Telegram/UI logic.

The project is intentionally developed in phases. Each phase introduces a meaningful capability and builds on the previous phase instead of adding everything at once.

---

# 2. Roadmap at a Glance

```text
PHASE 0
Project Planning & Architecture
        |
        v
PHASE 1
MVP: Language + Instagram + YouTube
        |
        v
PHASE 2
Reliability, Validation & User Experience
        |
        v
PHASE 3
Download Management & Resource Control
        |
        v
PHASE 4
Platform Expansion & Downloader Architecture
        |
        v
PHASE 5
Persistence, Database & User Features
        |
        v
PHASE 6
Background Jobs, Queue & Concurrency
        |
        v
PHASE 7
Security, Abuse Protection & Production Hardening
        |
        v
PHASE 8
Deployment, Monitoring & Scaling
```

The phases are intentionally ordered from **working product → reliable product → scalable product**.

---

# 3. Phase 0 — Project Planning & Architecture

## Goal

Establish a clear technical foundation before implementation begins.

## What we are trying to achieve

By the end of this phase, we should know:

- What the bot does.
- Which platforms are supported initially.
- How Instagram and YouTube behave differently.
- What each project module is responsible for.
- How language selection works.
- How temporary files are handled.
- How future functionality can be added without rewriting the project.

## Why this phase is necessary

Without a defined architecture, it is easy for a Telegram bot to become a single large file containing:

- Telegram handlers.
- `yt-dlp` configuration.
- URL detection.
- FFmpeg operations.
- File management.
- User preferences.
- Error handling.

That makes the project difficult to understand, test, and extend.

Phase 0 establishes boundaries before those problems appear.

## Concepts / technologies to learn

Focus only on the concepts required to understand this project:

- Python project structure.
- Python packages and modules.
- Separation of concerns.
- Basic layered architecture.
- Telegram Bot API concepts.
- `python-telegram-bot` basics.
- `yt-dlp` as a media extraction/download tool.
- FFmpeg's role in media processing.
- Environment variables.
- `.env` files.
- Git/GitHub project organization.
- Basic asynchronous programming concepts in Python.

## Tasks

- [ ] Create the repository.
- [ ] Create the agreed project structure.
- [ ] Set up the Python environment.
- [ ] Install the required Python dependencies.
- [ ] Install/configure FFmpeg.
- [ ] Create `.env.example`.
- [ ] Create `.gitignore`.
- [ ] Document the architecture.
- [ ] Define Phase 1 requirements.
- [ ] Confirm the Instagram quality policy.
- [ ] Confirm the YouTube quality-selection policy.
- [ ] Confirm the Persian/English language behavior.

## Phase 0 — Finalized Technical Decisions

These decisions were made during Phase 0 planning and constrain Phase 1 implementation. They are recorded here so future work (human or AI) does not silently re-decide them.

| Area | Decision |
|---|---|
| Project layout | Flat layout at the repository root (`bot/`, `config/`, `downloader/`, `services/`, `tests/`, `run.py`). The `README.md` does **not** use an `app/`-nested layout. |
| Language persistence (Phase 1) | SQLite. Accessed only through `services/language_service.py`; no other module touches storage directly. |
| Translation system | A centralized translation service that resolves a stable **message key** + the user's language code to localized text. The underlying storage format for translated strings (Python dict, JSON, YAML, etc.) is an implementation detail to be chosen in Phase 1, not in Phase 0. |
| `yt-dlp` version | Pinned in `requirements.txt` at `2026.8.19`. Upgrades are a deliberate, tested action, not automatic. |
| FFmpeg | Treated as a required **external system dependency**, not a Python package. The host must have FFmpeg installed and available on `PATH`. Phase 0 only documents this requirement; Phase 1 implements a startup validation check (see Phase 1 tasks) that fails fast with a clear error if FFmpeg is missing, rather than discovering this mid-download. Automatic installation of FFmpeg is explicitly out of scope; if containerized deployment is introduced later, FFmpeg becomes part of the image instead. |
| Python version | 3.14.4. |
| Testing framework | `pytest` as the primary framework, with `pytest-asyncio` for the bot's async code paths, and Python's built-in `unittest.mock` for isolating external dependencies (Telegram API, `yt-dlp`, FFmpeg). The standard test suite must not perform real network calls or real downloads; real-download tests, if introduced later, belong to a separate integration-test tier. |
| Instagram authentication | Phase 1 uses anonymous `yt-dlp` extraction only. The architecture must leave room for optional cookie/session-based authentication in a later phase. Any future credentials must be handled as configuration/secrets (e.g., via `.env`), never hardcoded or surfaced in user-facing Telegram messages. |
| Logging | Python's stdlib `logging` module. Phase 1 implements basic logging; Phase 2 expands it into the structured/diagnostic logging described in that phase. |
| YouTube single-quality videos | If a specific YouTube video only exposes one downloadable quality, the bot auto-downloads it rather than presenting a one-item menu, and explicitly tells the user that only one quality was available. This is a UX exception, not a change to the underlying policy: YouTube quality is still always *inspected* per video; the user is only skipped the selection step when there is nothing to select. |

## Expected result

A clean repository with a documented architecture and a clear development plan.

There does not need to be a complete working downloader yet.

## Before moving to Phase 1

You should understand:

- Why the project is divided into modules.
- What `handlers.py`, `video_service.py`, `manager.py`, and the downloader modules are responsible for.
- Why FFmpeg is needed.
- Why secrets belong in `.env`.
- The difference between Instagram's automatic quality behavior and YouTube's user-selected quality behavior.

## Dependencies

None. This is the foundation.

## Main components introduced

- Project structure.
- Configuration layer.
- Bot layer.
- Downloader layer.
- Service layer.
- File-management layer.
- Testing structure.

---

# 4. Phase 1 — MVP: Language + Instagram + YouTube

## Goal

Build the first complete end-to-end version of the bot.

This is the most important phase because it proves that the core product actually works.

## What we are trying to achieve

A user should be able to:

1. Start the bot.
2. Select Persian or English if they are a first-time user.
3. Have that preference remembered.
4. Change the language later.
5. Send an Instagram URL and receive the best available quality.
6. Send a YouTube URL.
7. See the qualities actually available for that YouTube video.
8. Select a quality.
9. Receive the selected YouTube video.
10. Have temporary files cleaned up.

## Why this phase is necessary

Before adding queues, databases, more platforms, scaling, or advanced features, we need a working product.

This phase answers the fundamental question:

> Can the entire Telegram → download → process → upload → cleanup pipeline work reliably?

If the answer is no, adding infrastructure will only make debugging harder.

## Concepts / technologies to learn

Project-specific concepts:

- Telegram commands.
- Telegram message handlers.
- Telegram callback queries.
- Inline keyboards.
- Telegram user IDs.
- User-specific state.
- `yt-dlp` URL extraction.
- `yt-dlp` format selection.
- Video/audio streams.
- FFmpeg merging.
- Temporary files.
- Basic async workflows.
- Exception handling.
- Basic logging.

## Tasks

### Bot foundation

- [ ] Start the Telegram bot.
- [ ] Implement `/start`.
- [ ] Implement basic user interaction.
- [ ] Create the initial main menu.
- [ ] Validate that FFmpeg is installed and available on `PATH` at startup; fail fast with a clear error if it is not.

### Language

- [ ] Detect first-time users.
- [ ] Show Persian/English selection.
- [ ] Save the selected language (SQLite, accessed only through `language_service.py`).
- [ ] Load the saved language for returning users.
- [ ] Add language switching.
- [ ] Centralize translated strings behind a lookup by message key + language code.
- [ ] Localize status messages.
- [ ] Localize errors.

### URL handling

- [ ] Receive URLs.
- [ ] Validate basic URL structure.
- [ ] Detect supported platforms.
- [ ] Reject unsupported URLs gracefully.

### Instagram

- [ ] Implement Instagram downloading.
- [ ] Select the best available quality automatically.
- [ ] Avoid intentionally reducing quality.
- [ ] Handle required FFmpeg processing.

### YouTube

- [ ] Extract available formats.
- [ ] Determine available video qualities.
- [ ] Display actual available qualities.
- [ ] Allow the user to select one.
- [ ] If only one quality is available, skip the menu, auto-download it, and inform the user only one quality existed.
- [ ] Download the selected quality.
- [ ] Merge audio/video when necessary.

### Delivery

- [ ] Send the downloaded video to the user.
- [ ] Delete temporary files.
- [ ] Handle failures without crashing the bot.

## Expected result

A functional MVP that can be demonstrated to another person.

Example:

```text
/start
   ↓
Choose: فارسی / English
   ↓
Main Menu
   ↓
Send YouTube URL
   ↓
Bot shows available qualities
   ↓
User selects 1080p
   ↓
Download
   ↓
Send video
   ↓
Cleanup
```

and:

```text
Send Instagram URL
   ↓
Download best available quality
   ↓
Send video
   ↓
Cleanup
```

## Before moving to Phase 2

You should be able to explain:

- The complete request lifecycle.
- How Telegram handlers communicate with the service layer.
- How platform detection works conceptually.
- Why YouTube needs a quality-selection step.
- Why Instagram does not need one.
- When FFmpeg is involved.
- How the user's language preference is retrieved and changed.
- How temporary files are created and removed.
- How errors move from the downloader to the user-facing layer.

You should also be able to run and demonstrate the MVP yourself.

## Dependencies

Requires Phase 0.

## Main components introduced

- `/start`.
- Language selection.
- Language persistence.
- Language switching.
- URL handling.
- Platform detection.
- Instagram downloader.
- YouTube downloader.
- Downloader manager.
- Video service.
- File service.
- Telegram upload.
- Basic error handling.

---

# 5. Phase 2 — Reliability, Validation & User Experience

## Goal

Turn the working MVP into a bot that behaves predictably when users do unexpected things.

## What we are trying to achieve

The bot should remain stable when:

- A user sends an invalid URL.
- A URL is unsupported.
- A video is unavailable.
- A download fails.
- A video has unusual formats.
- FFmpeg fails.
- Telegram cannot upload the file.
- Multiple users interact with the bot.
- A user presses an old/stale button.
- A user sends multiple requests.

The user experience should also become clearer and more polished.

## Why this phase is necessary

Phase 1 proves functionality.

Phase 2 proves **reliability**.

A bot that works only when everything goes perfectly is not a usable application.

## Concepts / technologies to learn

- Exception hierarchy.
- Defensive programming.
- Structured logging.
- Input validation.
- Callback-query state.
- Timeouts.
- Retry concepts.
- Telegram API limitations relevant to file uploads.
- User-facing error design.
- Testing with failure cases.
- Unit tests and integration tests.

## Tasks

### Validation

- [ ] Improve URL validation.
- [ ] Detect malformed URLs.
- [ ] Detect unsupported platforms.
- [ ] Handle unavailable/private/deleted media.

### Error handling

- [ ] Categorize download failures.
- [ ] Handle FFmpeg failures.
- [ ] Handle Telegram upload failures.
- [ ] Handle unexpected exceptions.
- [ ] Ensure users receive understandable messages.

### Logging

- [ ] Add consistent application logs.
- [ ] Log important failures.
- [ ] Avoid logging secrets.
- [ ] Include enough context to diagnose problems.

### User experience

- [ ] Improve status messages.
- [ ] Improve language-specific messages.
- [ ] Improve quality-selection UI.
- [ ] Handle stale callback buttons.
- [ ] Add clear retry/cancel behavior where appropriate.

### Testing

- [ ] Test valid URLs.
- [ ] Test invalid URLs.
- [ ] Test both languages.
- [ ] Test language switching.
- [ ] Test Instagram downloads.
- [ ] Test YouTube quality selection.
- [ ] Test failed downloads.
- [ ] Test cleanup after failures.

## Expected result

The bot should fail gracefully instead of crashing or leaving users confused.

## Before moving to Phase 3

You should understand:

- How to diagnose a failed download from logs.
- How to distinguish user errors from system errors.
- How callback-based Telegram interactions work.
- How to test failure paths.
- Why cleanup must happen even when an operation fails.

## Dependencies

Requires a working Phase 1 MVP.

## Main components introduced/developed

- Robust validation.
- Error-handling layer.
- Logging.
- Better callback/state handling.
- Expanded automated tests.
- Improved UI feedback.

---

# 6. Phase 3 — Download Management & Resource Control

## Goal

Control downloads so the bot does not waste disk space, memory, bandwidth, or processing capacity.

## What we are trying to achieve

The bot should safely handle real usage rather than assuming every download is small and fast.

Examples of concerns:

- Very large videos.
- Long-running downloads.
- Temporary files consuming disk space.
- Multiple users downloading simultaneously.
- Excessive requests from one user.
- Failed downloads leaving files behind.

## Why this phase is necessary

Media downloading is resource-intensive.

Without limits and cleanup policies, a few users can consume the machine's:

- Disk space.
- CPU.
- RAM.
- Network bandwidth.
- FFmpeg processing capacity.

## Concepts / technologies to learn

- Resource management.
- File-size limits.
- Disk-space checks.
- Rate limiting.
- Concurrency limits.
- Temporary-file lifecycle.
- Process management.
- Download cancellation.
- Timeouts.
- Basic performance profiling.

## Tasks

- [ ] Define maximum acceptable download size.
- [ ] Check available disk space.
- [ ] Improve temporary directory management.
- [ ] Guarantee cleanup on every failure path.
- [ ] Add download timeouts where appropriate.
- [ ] Limit concurrent downloads.
- [ ] Add per-user request limits.
- [ ] Prevent duplicate/uncontrolled downloads.
- [ ] Track active downloads in memory.
- [ ] Add cancellation handling if supported by the UI.

## Expected result

The bot can handle multiple requests without uncontrolled resource consumption.

## Before moving to Phase 4

You should understand:

- Why downloads must be bounded.
- How concurrent downloads affect CPU, RAM, disk, and network.
- How to distinguish application-level concurrency from Telegram updates.
- How temporary media lifecycle should be managed.

## Dependencies

Requires Phase 2 reliability and logging.

## Main components introduced/developed

- Resource limits.
- Concurrency control.
- Rate limiting.
- Disk-space management.
- Download lifecycle management.
- Better cleanup.

---

# 7. Phase 4 — Platform Expansion & Downloader Architecture

## Goal

Make the downloader architecture strong enough to support additional platforms without damaging existing functionality.

## What we are trying to achieve

The project should be able to add another supported platform by introducing a new downloader implementation rather than rewriting the bot.

Conceptually:

```text
                    Downloader Manager
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
     YouTube           Instagram          Platform X
```

The Telegram layer should not care how each platform is downloaded.

## Why this phase is necessary

As more platforms are added, platform-specific rules become increasingly different.

Keeping those rules isolated prevents:

- Huge handlers.
- Giant conditional statements.
- Duplicated download logic.
- Platform-specific bugs affecting unrelated platforms.

## Concepts / technologies to learn

- Strategy pattern.
- Interfaces/abstractions.
- Polymorphism.
- Dependency inversion at a practical level.
- Platform-specific media extraction.
- Format normalization.
- Capability detection.
- Adapter-style architecture.

## Tasks

- [ ] Review the downloader manager.
- [ ] Define a consistent downloader contract.
- [ ] Keep YouTube logic isolated.
- [ ] Keep Instagram logic isolated.
- [ ] Add another platform only when there is a real requirement.
- [ ] Normalize downloader results.
- [ ] Ensure platform-specific failures remain isolated.
- [ ] Expand downloader tests.

## Expected result

A new downloader can be added without modifying the core Telegram workflow significantly.

## Before moving to Phase 5

You should be able to explain:

- Why the downloader manager exists.
- Why platform-specific logic belongs in separate modules.
- What information a downloader should return to the service layer.
- How an abstraction prevents platform-specific code from spreading through the application.

## Dependencies

Requires the stable downloader and service architecture from Phases 1–3.

## Main components introduced/developed

- Downloader abstraction.
- Expanded downloader manager.
- Additional platform modules.
- Platform capability detection.
- More comprehensive downloader testing.

---

# 8. Phase 5 — Persistence, Database & User Features

## Goal

Introduce durable storage for user information and future persistent features.

## What we are trying to achieve

The bot should be able to persist information beyond the lifetime of a process.

Potential data includes:

```text
User
 ├── Telegram ID
 ├── Language
 ├── Created date
 ├── Last activity
 └── Preferences
```

Potential future history:

```text
Download
 ├── User
 ├── Platform
 ├── URL / source identifier
 ├── Quality
 ├── Status
 └── Timestamp
```

## Why this phase is necessary

Early development can use simple preference storage, but persistent user features eventually require a proper data model.

A database becomes especially useful when adding:

- User preferences.
- Download history.
- Usage statistics.
- Limits.
- Subscriptions.
- Administrative features.

## Concepts / technologies to learn

- Relational databases.
- SQL.
- Tables and relationships.
- Primary/foreign keys.
- Indexes.
- Transactions.
- Database migrations.
- ORM concepts.
- Connection management.
- Data modeling.

A suitable database technology can be selected when this phase begins; the architecture should not assume a specific database prematurely.

## Tasks

- [ ] Define user data requirements.
- [ ] Define database schema.
- [ ] Move persistent language preferences to database storage if appropriate.
- [ ] Add database access layer.
- [ ] Separate database logic from business logic.
- [ ] Add migrations.
- [ ] Add tests for persistence.
- [ ] Decide whether download history is required.
- [ ] Define data-retention rules.

## Expected result

User preferences and future persistent features are stored reliably and survive bot restarts.

## Before moving to Phase 6

You should understand:

- Why a database is different from temporary application state.
- How relational data is modeled.
- How transactions protect data consistency.
- Why database access should not be mixed into Telegram handlers.
- How migrations work.

## Dependencies

Requires stable application behavior and clearly defined persistent requirements.

## Main components introduced/developed

- Database.
- User model.
- Preference persistence.
- Database access layer.
- Migration system.
- Optional download-history model.

---

# 9. Phase 6 — Background Jobs, Queue & Concurrency

## Goal

Separate long-running media downloads from the Telegram update-handling process.

## What we are trying to achieve

The bot should remain responsive while downloads are running.

Conceptually:

```text
Telegram Update
      |
      v
Create Download Job
      |
      v
Queue
      |
      v
Worker
      |
      v
yt-dlp / FFmpeg
      |
      v
Result
      |
      v
Telegram
```

Instead of treating every download as a simple immediate operation, the system manages downloads as jobs.

## Why this phase is necessary

Video downloads can take a long time.

As usage increases, directly processing every download inside the main bot workflow can cause:

- Slow responses.
- Too many simultaneous processes.
- Resource exhaustion.
- Poor cancellation behavior.
- Difficult workload management.

## Concepts / technologies to learn

- Async programming.
- Concurrency.
- Worker processes.
- Job queues.
- Producer/consumer architecture.
- Background tasks.
- Job states.
- Retry policies.
- Cancellation.
- Idempotency.
- Process isolation.

## Tasks

- [ ] Define download-job states.
- [ ] Separate request creation from download execution.
- [ ] Introduce a queue.
- [ ] Create worker logic.
- [ ] Limit worker concurrency.
- [ ] Track job status.
- [ ] Handle failed jobs.
- [ ] Handle retries carefully.
- [ ] Handle cancellation.
- [ ] Connect job completion back to Telegram.

## Expected result

The Telegram bot remains responsive while downloads are processed by controlled workers.

## Before moving to Phase 7

You should understand:

- Why background workers are useful.
- How a queue controls workload.
- Difference between asynchronous I/O and CPU/process-heavy work.
- Why FFmpeg processes need resource limits.
- How job state should be tracked.

## Dependencies

Strongly depends on Phases 2–5.

## Main components introduced/developed

- Download job model.
- Queue.
- Worker system.
- Concurrency control.
- Job status tracking.
- Retry/cancellation mechanisms.

---

# 10. Phase 7 — Security, Abuse Protection & Production Hardening

## Goal

Prepare the application for untrusted public users.

## What we are trying to achieve

The bot should assume users may intentionally or unintentionally send problematic requests.

Protection should cover:

- Excessive requests.
- Extremely large downloads.
- Malicious or malformed input.
- Resource exhaustion.
- Secret exposure.
- Unsafe file handling.
- Unexpected process behavior.

## Why this phase is necessary

A private development bot and a public Internet-facing bot have very different threat models.

A downloader bot is particularly sensitive because users control URLs and can indirectly control:

- Network requests.
- Download duration.
- File size.
- Media processing.
- FFmpeg workload.

## Concepts / technologies to learn

- Threat modeling.
- Input sanitization.
- Rate limiting.
- Authentication/authorization concepts.
- Secret management.
- Secure file handling.
- Process isolation.
- Least privilege.
- Dependency security.
- Secure logging.
- Abuse prevention.

## Tasks

- [ ] Review every user-controlled input.
- [ ] Harden URL handling.
- [ ] Review temporary-file paths.
- [ ] Prevent path traversal.
- [ ] Enforce download limits.
- [ ] Enforce request limits.
- [ ] Protect bot credentials.
- [ ] Review dependencies.
- [ ] Avoid sensitive information in logs.
- [ ] Define abuse policies.
- [ ] Test resource-exhaustion scenarios.
- [ ] Review FFmpeg/yt-dlp execution boundaries.

## Expected result

The application is substantially safer to expose to real users.

## Before moving to Phase 8

You should understand:

- The main attack surfaces of this specific bot.
- Why user-controlled URLs are security-sensitive.
- Why resource limits are part of security.
- How secrets should be managed.
- How to distinguish operational failures from security events.

## Dependencies

Requires the architecture, persistence, and resource controls from earlier phases.

## Main components introduced/developed

- Security controls.
- Abuse protection.
- Rate limiting.
- Secure configuration.
- Hardened file/process handling.
- Security-oriented logging and monitoring hooks.

---

# 11. Phase 8 — Deployment, Monitoring & Scaling

## Goal

Run the bot reliably as a production service.

## What we are trying to achieve

The final system should be deployable and maintainable on a server.

It should support:

- Automatic startup.
- Configuration through environment variables.
- Persistent data.
- Log collection.
- Health monitoring.
- Failure recovery.
- Controlled updates.
- Backup/recovery procedures.
- Scaling when necessary.

## Why this phase is necessary

A project that only works on a development PC is not yet a production service.

Production introduces operational problems such as:

- Process crashes.
- Server restarts.
- Disk exhaustion.
- Network failures.
- Dependency updates.
- Database failures.
- Monitoring gaps.

## Concepts / technologies to learn

- Linux server basics.
- Process managers.
- Docker/containerization.
- Environment configuration.
- Reverse proxies where applicable.
- CI/CD basics.
- Health checks.
- Monitoring.
- Metrics.
- Log aggregation.
- Backups.
- Deployment strategies.
- Service recovery.

## Tasks

- [ ] Choose a deployment environment.
- [ ] Containerize if appropriate.
- [ ] Configure production environment variables.
- [ ] Configure persistent storage.
- [ ] Configure database backups.
- [ ] Configure application logs.
- [ ] Add health checks.
- [ ] Add monitoring.
- [ ] Configure automatic restart.
- [ ] Establish update/deployment procedure.
- [ ] Document recovery procedures.
- [ ] Perform production load testing.
- [ ] Review operational limits.

## Expected result

The bot runs as a maintainable production service rather than as a manually started development application.

## Before considering the project production-ready

You should be able to:

- Deploy the bot from scratch.
- Restart it safely.
- Diagnose common failures.
- Recover from application crashes.
- Restore persistent data.
- Check resource usage.
- Understand where logs and metrics come from.
- Update the application without losing important data.

## Dependencies

Requires all previous phases that are relevant to the selected production architecture.

## Main components introduced/developed

- Deployment configuration.
- Containerization if selected.
- Monitoring.
- Health checks.
- Backup/recovery.
- Production logging.
- CI/CD where appropriate.

---

# 12. Phase Dependencies

The roadmap should generally follow this dependency chain:

```text
Phase 0
  |
  v
Phase 1
  |
  v
Phase 2
  |
  v
Phase 3
  |
  +--------------------+
  |                    |
  v                    v
Phase 4              Phase 5
  |                    |
  +---------+----------+
            |
            v
         Phase 6
            |
            v
         Phase 7
            |
            v
         Phase 8
```

### Important

The phases are not merely arbitrary feature groups.

Each phase solves a different class of problem:

```text
Phase 0 → What are we building?
Phase 1 → Does it work?
Phase 2 → Does it fail gracefully?
Phase 3 → Can we control resource usage?
Phase 4 → Can we expand platforms cleanly?
Phase 5 → Can we persist user/application data?
Phase 6 → Can we handle long-running work at scale?
Phase 7 → Can we safely expose it to users?
Phase 8 → Can we operate it reliably in production?
```

---

# 13. Learning Progression

The project should also be treated as a learning path.

## After Phase 0

You should understand:

- Python project organization.
- The project's architecture.
- Telegram bot fundamentals.
- `yt-dlp` and FFmpeg roles.
- Environment configuration.

## After Phase 1

You should understand:

- Telegram handlers.
- Inline keyboards.
- Callback queries.
- User preferences.
- Basic async workflows.
- Media downloading.
- Format selection.
- FFmpeg integration.
- Temporary files.

## After Phase 2

You should understand:

- Robust error handling.
- Logging.
- Testing.
- Failure-path design.
- Better Telegram UX.

## After Phase 3

You should understand:

- Resource management.
- Rate limiting.
- Concurrency limits.
- Download lifecycle management.

## After Phase 4

You should understand:

- Modular downloader architecture.
- Abstractions.
- Strategy-style designs.
- Platform-specific integrations.

## After Phase 5

You should understand:

- SQL/database fundamentals.
- Data modeling.
- Persistence.
- Transactions.
- Migrations.

## After Phase 6

You should understand:

- Queues.
- Workers.
- Background jobs.
- Concurrency.
- Job state management.

## After Phase 7

You should understand:

- Threat modeling.
- Input security.
- Abuse prevention.
- Secure configuration.
- Resource-based attacks.

## After Phase 8

You should understand:

- Production deployment.
- Containers/process management.
- Monitoring.
- Backups.
- Operational troubleshooting.
- Basic scaling.

---

# 14. Roadmap Completion Definition

The project should be considered **fully developed** when:

### Product

- [ ] Users can select Persian or English.
- [ ] Language preferences persist.
- [ ] Users can change language.
- [ ] Instagram videos download at the best available quality.
- [ ] YouTube videos provide actual available quality choices.
- [ ] Selected YouTube quality is downloaded.
- [ ] FFmpeg processing works when required.
- [ ] Videos are delivered through Telegram.

### Reliability

- [ ] Invalid requests are handled.
- [ ] Download failures are handled.
- [ ] Telegram failures are handled.
- [ ] Temporary files are cleaned up.
- [ ] Logs provide useful diagnostic information.
- [ ] Automated tests cover critical functionality.

### Resource management

- [ ] Download size limits exist.
- [ ] Concurrency is controlled.
- [ ] Rate limits exist.
- [ ] Disk usage is controlled.
- [ ] Long-running jobs are manageable.

### Architecture

- [ ] Telegram logic is separated from download logic.
- [ ] Platform-specific logic is isolated.
- [ ] User preferences are separated from UI logic.
- [ ] Persistent data is separated from business logic.
- [ ] Background jobs are separated from update handling.

### Security

- [ ] Secrets are protected.
- [ ] User-controlled input is validated.
- [ ] File handling is hardened.
- [ ] Abuse controls exist.
- [ ] Dependencies are maintained.

### Operations

- [ ] The bot can be deployed reproducibly.
- [ ] The application can recover from crashes.
- [ ] Monitoring exists.
- [ ] Logs can be inspected.
- [ ] Persistent data can be backed up and restored.

---

# 15. AI Development Rules

This section exists specifically so future AI assistants working on the repository can understand how development should proceed.

## Rule 1 — Respect the current phase

Do not implement features from a later phase merely because they seem useful.

If the project is in Phase 1, focus on Phase 1 requirements.

## Rule 2 — Do not skip dependencies

Before introducing a feature, verify which previous phase provides the required foundation.

## Rule 3 — Do not over-engineer Phase 1

Phase 1 is intended to prove the core product.

Do not introduce a complex queue, distributed worker architecture, or production database merely because those technologies may eventually be useful.

## Rule 4 — Preserve separation of concerns

Do not put:

- `yt-dlp` logic into Telegram handlers.
- Database queries into keyboards.
- Translation storage into downloader modules.
- File cleanup logic into platform-specific downloaders unless there is a specific reason.

## Rule 5 — Platform behavior must remain explicit

```text
Instagram → best available quality automatically

YouTube → inspect available qualities → user chooses
```

Do not silently change this behavior.

## Rule 6 — Language is a user preference

The language belongs to an individual Telegram user.

Changing one user's language must not change another user's language.

## Rule 7 — Prefer the smallest change that solves the current phase

Do not introduce architecture solely for hypothetical future requirements.

## Rule 8 — Update documentation when architecture changes

If implementation decisions materially change:

- Project structure.
- Phase scope.
- Dependencies.
- User behavior.
- Data model.
- Architecture.

Then update the relevant documentation.

---

# 16. Current Development Position

The project is currently preparing for:

## **Phase 1 — MVP**

The immediate target is:

```text
                ┌───────────────────┐
                │      /start       │
                └─────────┬─────────┘
                          |
                          v
                ┌───────────────────┐
                │ Language selected?│
                └─────────┬─────────┘
                          |
             +------------+------------+
             |                         |
             v                         v
       First-time user          Returning user
             |                         |
             v                         |
     Persian / English                 |
             |                         |
             +------------+------------+
                          |
                          v
                     Main Menu
                          |
                          v
                    User sends URL
                          |
                          v
                   Detect platform
                     /         \
                    /           \
                   v             v
              YouTube        Instagram
                  |               |
                  v               v
          Get available      Best available
             qualities          quality
                  |               |
                  v               |
           User chooses           |
             quality              |
                  |               |
                  +-------+-------+
                          |
                          v
                       Download
                          |
                          v
                  FFmpeg if needed
                          |
                          v
                     Send video
                          |
                          v
                       Cleanup
```

The next implementation work should therefore remain focused on this vertical slice.

---

# 17. Final Roadmap Philosophy

The project is not being built as one giant application from the beginning.

It is being built through controlled increases in complexity:

```text
                    PRODUCT COMPLEXITY

                         ▲
                         |
                         |                  Phase 8
                         |             Production/Scaling
                         |
                         |             Phase 7
                         |          Security/Hardening
                         |
                         |             Phase 6
                         |          Queue/Workers
                         |
                         |             Phase 5
                         |       Database/Persistence
                         |
                         |             Phase 4
                         |       Platform Expansion
                         |
                         |             Phase 3
                         |     Resource Management
                         |
                         |             Phase 2
                         |     Reliability/UX
                         |
                         |             Phase 1
                         |             MVP
                         |
                         |             Phase 0
                         |         Architecture
                         +-------------------------------->
                              DEVELOPMENT PROGRESSION
```

The guiding principle is:

> **Make it work → make it reliable → make it controlled → make it extensible → make it persistent → make it scalable → make it secure → make it production-ready.**

This roadmap should be treated as the project's high-level development contract. Individual implementation decisions may change as the project evolves, but every change should be evaluated against the purpose and dependencies of the current phase.
