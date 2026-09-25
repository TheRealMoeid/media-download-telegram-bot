# AI_COLLABORATION.md — Multi-Model Development Framework

> **Purpose of this file:** This project is now worked on by more than one AI model at a time, in separate sessions, often concurrently. This file explains *why*, defines how responsibilities are divided, and sets the rules that keep independent sessions from making conflicting decisions or silently duplicating/undoing each other's work. It does not replace `CLAUDE.md` (the technical reference) or `PROJECT_ROADMAP.md` (the phased plan) — it sits alongside them as the *process* layer. Read this file, `CLAUDE.md`, and `MODULES.md` together before starting any work; none of the three is sufficient alone once more than one model is active.
>
> This file is intentionally general — it describes how to divide *any* future work on this project, not just the two tracks active when it was written. `MODULES.md` is where the concrete, current module boundaries live and gets updated more often; this file should stay comparatively stable.

---

## 1. Why multiple models

Moeid has access to several AI models/tools and would rather run genuinely independent pieces of work in parallel than serialize everything through a single session. This is purely a throughput decision — it doesn't imply any model is better suited to one kind of task than another, and it doesn't create fixed "roles" (there is no permanently-assigned "YouTube model" or "Instagram model"). Any model can pick up any module, provided it actually reads the context this file and its companions require first.

The tradeoff this introduces: without a shared, explicit coordination system, parallel sessions can (a) silently re-decide something `CLAUDE.md` already settled, (b) both edit the same file without knowing about each other, or (c) leave the shared docs stale, which actively misleads whoever reads them next — human or model. Everything below exists to prevent those three failure modes specifically.

---

## 2. Single source of truth

`CLAUDE.md` (architecture, current state, issues) and `PROJECT_ROADMAP.md` (phased plan, task checklists) remain the **only** authoritative record of project state. A decision, a finding, or a completed step that exists only in one model's own chat history is invisible to every other session — as far as the project is concerned, **it did not happen** until it's written into one of these files.

This means:
- Any model finishing a piece of work updates the relevant sections of `CLAUDE.md`/`PROJECT_ROADMAP.md` **before** considering that work done — not "at some point later," not "if there's time." An unfinished task with honest docs is fine. A finished task with stale docs actively costs the next session time and trust.
- Any model that discovers something material mid-task (a bug, a ruled-out hypothesis, an environment fact) writes it down immediately, even if the overall task isn't finished — see Issue #5 in `CLAUDE.md` for the model this follows: incremental findings, appended as they happen, not reconstructed from memory at the end.
- If a model believes an existing documented decision (`CLAUDE.md` §3's "Finalized architecture decisions," the 8 AI Development Rules in `PROJECT_ROADMAP.md` §15, or Phase 0's decisions table) needs revisiting, it **stops and asks Moeid** rather than quietly working around it or reinterpreting it. These decisions exist specifically so they don't get silently re-litigated by whoever happens to be working on the code next.

---

## 3. How responsibilities are divided

Work is assigned by **module boundary**, not by arbitrary task description. `MODULES.md` defines the current set of modules, each with a clear file list and dependency map. The rule is simple:

- **One module, one active session at a time.** Two models should never be mid-task on the same module concurrently — if `MODULES.md` shows two candidate tasks touch the same module, they go to the same session, sequentially, not two sessions in parallel.
- **Prefer assigning whole modules, not slices of a module.** Splitting a single module's files across two concurrent sessions (e.g., one model editing `bot/handlers.py` while another edits `bot/keyboards.py` for the same feature) is exactly the kind of fine-grained split this project is trying to avoid — per `MODULES.md`, those two files belong to the same module precisely because they change together.
- **Higher-collision-risk files get named explicitly** in any task handed to a model, with an instruction to leave them alone unless the task specifically requires them. See `MODULES.md`'s "Shared / high-collision-risk files" section — `bot/handlers.py`, `bot/keyboards.py`, `CLAUDE.md`, `PROJECT_ROADMAP.md`, and `requirements.txt` are the current ones.

---

## 4. Conflict prevention rules

1. **Never touch a module outside your assigned scope without explicit sign-off from Moeid.** If a task seems to require it (e.g., a YouTube-extraction fix that seems to need a handler change), stop and flag it rather than making the change and explaining it after the fact.
2. **Treat `CLAUDE.md` §3 and `PROJECT_ROADMAP.md`'s Phase 0 decisions table as read-only during normal work.** These are cross-session contracts. Amending them is itself a task that needs Moeid's explicit go-ahead, not a side effect of an unrelated change.
3. **When in doubt about whether a file is "yours" for the current task, check `MODULES.md` first, then ask.** Guessing costs less up front than a collision costs later.
4. **A model should never assume its own session's understanding of "current state" is complete.** Before starting, re-read `CLAUDE.md` §2 (status table) fully — another parallel session may have changed it since this model's context was last refreshed.
5. **Git branching stays one branch per track**, matching the convention already established in `CLAUDE.md` §7 (short-lived feature branches merged into `phase-1`). Two parallel tracks get two separate branches; Moeid remains the one who merges, not the models.

---

## 5. What a model should receive before starting work

Whoever hands off a task to a model (Moeid, directly, in each case — models do not currently hand tasks to each other) should ensure the model has:

1. **`CLAUDE.md`, in full.** Not a summary — the actual current file. This is non-negotiable; see `CLAUDE.md` §11 and this file's own onboarding note.
2. **`AI_COLLABORATION.md` (this file) and `MODULES.md`, in full.**
3. **The relevant section(s) of `PROJECT_ROADMAP.md`** — usually just the current phase's task list and the Phase 0 decisions table, not the entire 9-phase document.
4. **A clear, explicit statement of scope**: which module(s) this task covers, and — just as important — which files/modules are explicitly *out of scope* for this task. See `CLAUDE.md` §2's Track A/Track B split for the current example of how this should read.
5. **Any directly relevant open issues from `CLAUDE.md` §8**, called out by name (e.g., "read Issue #5 in full before proposing anything" for YouTube-extraction work) — don't rely on the model finding them unprompted inside a long file.

If any of the above is missing, the receiving model should ask for it before proceeding, rather than filling the gap with assumptions.

---

## 6. How completed work should be handed off

A task is not "done" until all of the following are true, not just the first one:

1. **The code/deliverable itself works** — tests pass, and for anything user-facing, it's been exercised the way the project's existing conventions require (see `CLAUDE.md` §6 for testing conventions, §9 for how Moeid likes to manually verify things).
2. **`CLAUDE.md` is updated**: the status table (§2), the relevant module notes (§5), any new issues or resolved ones (§8), and the open-items backlog (§10) if applicable.
3. **`PROJECT_ROADMAP.md` is updated** if task checkboxes or phase status changed.
4. **What was explicitly *not* done, and why, is stated plainly** — an honest "I didn't get to X" is far more useful to the next session than silence that lets someone assume X is done.
5. **Any new open questions, ruled-out approaches, or constraints discovered along the way are written down** — not just the final successful path. `CLAUDE.md`'s Issue #5 is the model for this: a fix that looked promising and got ruled out is exactly as valuable to document as one that worked, because it stops the next session from re-trying it.

Moeid remains the integration point: he applies patches/files, merges branches, and is the one who ultimately decides when two parallel tracks are ready to be brought together. Models do not merge each other's work directly.

---

## 7. A note on documentation collisions specifically

`CLAUDE.md` and `PROJECT_ROADMAP.md` are themselves shared, high-collision-risk files (see `MODULES.md`) — if two tracks finish around the same time, both will want to update the same status table. In practice:

- Whichever track's work Moeid applies/merges *first* gets its documentation update applied first; the second track's model should **re-read the current file state before writing its own update**, not blindly apply an update drafted against a now-stale baseline (this is the same lesson as `CLAUDE.md`'s Issue #4, generalized to a multi-model context: don't trust remembered file content when the live file might have changed).
- If a documentation patch fails to apply because the file moved on underneath it, that's expected in a multi-track workflow, not a bug — regenerate the update against the current file rather than forcing an outdated patch through.

---

## 8. Applying this beyond the current two tracks

This framework isn't specific to "Instagram delivery" and "YouTube extraction." Any time Moeid identifies two or more pieces of work that `MODULES.md` shows don't share files, they're candidates for parallel assignment using this same process: define scope explicitly, hand each session the reading list in §5, and require the handoff checklist in §6 before either is considered finished. See `MODULES.md` for the current, evolving map of what those independent pieces are.
