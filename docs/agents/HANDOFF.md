# Handoff protocol (every agent, every tool)

Agents come and go mid-task: Claude writes a feature, ChatGPT reviews it, Gemini fixes the bug it found, Grok picks up
the next item. The repo is the only memory they share, so these files have to be current.

| File | Who writes | When |
|---|---|---|
| `.handoffs/LATEST.md` | the agent ending a session | **overwrite** before handing off: the savestate |
| `.claudes/breadcrumbs.md` (or `<folder>/.claudes/`) | same | **append** a dated entry (history; never rewrite old ones) |
| `<folder>/CLAUDE.md` | anyone who changes structure | when files, conventions or open work change |
| `AGENTS.md` | rarely | only for repo-wide rules or layout changes |

## Starting a session

1. Read `agents.txt` → `.handoffs/LATEST.md` → `AGENTS.md` → the folder map you need. Don't re-scan the repo.
2. `git fetch` and check "In Flight" in LATEST.md. If another agent owns your topic, don't start: say so.
3. Branch `<agent>/<topic>` from `origin/main` (or from the branch you're continuing).
4. Add your line to "In Flight" in LATEST.md and commit it first, so others see the claim.

## Ending a session (or switching models)

1. Commit and push. Never leave work only in a local checkout or a chat.
2. Overwrite `.handoffs/LATEST.md`, keeping its four sections:
   - **📍 Where We Stopped**: active task, current state, blockers/bugs.
   - **🛠️ Environmental Verification**: last test run and result (PASSED/FAILED, which test), exact command to re-run.
   - **📦 Changes Introduced in This Session**: files created/modified, one line each.
   - **⏭️ Precise Next Steps for Incoming Model**: numbered `[ ]` checkboxes, concrete enough to start without asking.
   Update your "In Flight" line (or remove it when the PR is merged).
3. Append a dated entry to `.claudes/breadcrumbs.md`: what changed, why, what was measured, dead ends tried.
4. Update the folder map if you changed structure or finished an "Open work" item.

## Bug work

1. Reproduce first (test, script or exact steps) and write the reproduction into LATEST.md before fixing.
2. Fix in the smallest diff. Add a test that fails before and passes after when the folder has tests.
3. If the same logic exists in another app (web ↔ linux ↔ ios-suite), say so in the PR's "Other apps" section;
   fix there too or add it to Next Steps.

## Feature work

1. Check LATEST.md "Waiting on Jonah": some features need his go before anyone starts.
2. Write a 3-5 line plan in the PR description first (draft PR is fine), then build.
3. User-facing change → a line in that folder's CHANGELOG.md, written for Jonah, not for developers.

## Code review (reviewing another agent's PR)

Follow [REVIEW.md](REVIEW.md). Review comments go on the PR; don't push to someone else's branch unless asked.
The author answers or fixes, then re-requests review. Only Jonah merges.

## Commit and PR style

- Commit message: one plain sentence of what changed for the user. Trailer `Agent: <name/model>` is welcome.
- PR: fill in `.github/pull_request_template.md`. One topic per PR.
