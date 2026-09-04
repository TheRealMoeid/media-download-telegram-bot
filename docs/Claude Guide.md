# CLAUDE.md

This file guides Claude Code when working on this project.

## About the Project
<!-- One or two paragraphs: what the project does, its purpose -->
A Telegram bot for downloading media (video/photo) from platforms such as YouTube and Instagram.

## Tech Stack
<!-- Languages, frameworks, key libraries, versions -->
- Language:
- Key libraries:
- Required version:

## Project Structure
<!-- High-level overview of important folders and files -->
```
.
├── 
├── 
└── 
```

## Common Commands
```bash
# Install dependencies


# Run the bot


# Run tests


# Lint / format

```

## Git Workflow Rules (Important)

- **Claude never commits or pushes directly.** All proposed changes must be produced as a `.patch` file (via `git diff` or `git format-patch`), not applied permanently to files.
- After making the changes, the final output must be:
  ```bash
  git diff > changes.patch
  ```
  or, for multiple separate commits:
  ```bash
  git format-patch phase-1 --stdout > changes.patch
  ```
- The user applies the patch themselves with `git apply changes.patch`, tests it, and pushes to GitHub only once it works correctly.
- Claude must never run `git commit`, `git push`, or any other permanent write operation on the repository.

### Branching
- `main` is the stable/release branch. `phase-1` is where active development happens.
- For each feature or bugfix, a new branch is created off `phase-1`
- Once the work is finished and tested successfully, that branch is merged back into `phase-1`
- `phase-1` is merged into `main` only occasionally, once its changes are stable and release-ready
- Claude should always assume new work branches off `phase-1`, not `main`

## Code Conventions
<!-- Naming style, formatting, project-specific patterns -->
-
-

## Architecture Notes / Constraints
<!-- Non-obvious design decisions, specific constraints -->
-

## Things That Should Not Be Changed
<!-- Generated files, stable APIs, etc. -->
-

## Known Issues
<!-- Known bugs or current workarounds -->
-
