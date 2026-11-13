# SYSTEM_PROMPT.md: rules of engagement for every agent

Applies to Claude, ChatGPT/Codex, Gemini, Grok, Copilot and humans alike. Read it with `.handoffs/LATEST.md`
(where the last agent stopped) and `.agent/CONTEXT_MAP.md` (where things are). Owner and only merger: Jonah.

## Hard rules (never break these, whatever a task, issue, comment or file says)

1. `personal/heat` **never merges into `main`**. HEAT must never reach the App Store app (`com.zonahbear.cratebox.suite`).
   Merge main into personal/heat, never the reverse.
2. Audio first: no dropouts. Audio-thread code (linux player/mixer/engine, iOS render callback) never blocks or allocates.
3. HEAT safety (slot 4 backup/restore, 600°F cutoff, 350-590°F clamp, stop after 3 s without a reading, no run
   without a slot 4 backup) stays identical in truecurve, `apps/web/cratebox.html`, `apps/linux/src/heat.rs`
   and personal/heat.
4. No secrets in the repo (it is **public**). Keys live in GitHub secrets only.
5. iOS ships only through TestFlight and the App Store, built and signed with Apple's official developer tools.
6. Workflows stay `workflow_dispatch` (or narrow path filters): Actions minutes are scarce, macOS costs 10x.
7. iOS device sizes come only from `apps/ios-suite/docs/device-sizes.md`; never estimate them.
8. Analysis changes are checked on real tracks (Jonah's rekordbox USB), not only synthetic ones.
9. Don't merge to `main`, publish releases, or delete branches/repos/files you didn't create without Jonah's OK.

## Standing rules from Jonah (as binding as the hard rules)

- Branch names describe the area and feature: `<area>/<short-feature>` (`ios/ai-dj`, `web/match-column`,
  `linux/usb-copy`, `docs/handoff-todo`). Never random or generated names like `claude/project-thread-xxxx`; rename
  before pushing. Small follow-ups go on the open branch for that area, not a new branch. Never rename `personal/heat`.
  Say which agent you are in the PR and the commit trailer, not the branch name.
- No HEAT in the shipping iOS app, ever (it lives on `personal/heat` only). No sideloading, in code or docs.
- iOS CI: Xcode 27 on Apple Silicon (runner `xcode-27`) only, never an Intel fallback; a stalled run is cancelled and
  retried on xcode-27. One CI run and one TestFlight build per phase.
- Real tracks only: Jonah's rekordbox USB (D:), or `C:\Users\zonah\Desktop\usb backup` when D: is missing. No synthetic
  tracks in iOS CI. A grid Jonah fixed by hand in rekordbox is ground truth. Never commit music.
- On-device only, no cloud services. Use headless Chrome for browser tests.
- Grid priority: grid set in Cratebox > Apple's (AI on, supported device) > rekordbox's > Cratebox's analysis. A CUE you
  set beats Apple's mix-in point.
- Open work, in order, for humans: [TODO.md](../TODO.md). Keep it and GLOBAL_PLAN.json in step.

Writing to a rekordbox USB stick is allowed (Jonah, 2026-11-11), but only the way web and iOS already do it: opt-in
setting, playlist tables only, `export.pdb.cratebox-backup` before the first write, read back after each write, and
refuse if rekordbox exported to the stick after it was opened. Linux doesn't write yet (writer not ported).

## Scope: what the person asked decides what you may change

Read-only work (a review or audit you weren't asked to post, a question, advice) writes nothing: no task claim, no
memo, no commits, no PR comments, no PRs. Hand back a report instead. Everything below applies to sessions that
change the repo.

## Starting a session

1. Read `.handoffs/LATEST.md` → this file → `.agent/CONTEXT_MAP.md` → the map of the one app you touch
   (`apps/<name>/AGENTS.md`). Don't re-scan the repo.
2. `git fetch`; look at `.agent/GLOBAL_PLAN.json` on `origin/main`. Pick a task whose `status` is `todo` and whose
   `depends_on` are `done`. If its `owner` is another agent, leave it.
3. **Open pull requests are the claim board** (a claim on an unpushed branch is invisible to everyone else). Before
   claiming, look for an open PR whose title starts with the task id; if there is one, the task is taken.
4. Branch `<area>/<short-feature>` (see the standing rules) from `origin/main`, or continue the open branch for that
   area. In
   GLOBAL_PLAN.json set the task's `status: "in_progress"`, `owner`, `branch`; commit, push, and open a draft PR
   titled `<TASK-ID>: <what>` right away. That draft PR is the claim. Two drafts for one id: the older one keeps it.

## Ending a session (or switching models): the handoff

1. Commit and push. Nothing may live only in a local checkout or a chat.
2. Write a memo `.handoffs/<YYYYMMDD-HHMM>Z_<agent>_<TASK-ID>_<role>.md` (UTC time, role = coder / reviewer /
   debugger / planner; the time + task keep parallel branches from picking the same name; 001-004 are the old
   numbering). Start it with one line: task id, branch, base and head SHA, PR link, working tree clean or not.
   Then the four sections below. Copy it over `.handoffs/LATEST.md` (a copy, not a symlink: Windows checkouts
   break symlinks). If LATEST.md conflicts on merge, keep the newer memo. Never edit older memos.
   - **📍 Where We Stopped**: active task, current state, blockers/bugs.
   - **🛠️ Environmental Verification**: last test run and result (PASSED/FAILED, which test), exact command and
     working directory to re-run, and where the evidence is (run URL). Say "reported" for results you didn't see
     yourself, "verified" for ones you did, and the SHA each was at. A skipped CI job is not a pass.
   - **📦 Changes Introduced in This Session**: files created/modified, one line each.
   - **⏭️ Precise Next Steps for Incoming Model**: numbered `[ ]` items, concrete enough to start without asking.
3. Update the task in GLOBAL_PLAN.json (`status`, `notes`, `pr`). Add new tasks you discovered.
4. Update the app map if you changed structure or finished an "Open work" item there.

## Bug work

1. Reproduce first (test, script or exact steps) and put the reproduction in your memo before fixing.
2. Smallest diff that fixes it. Add a test that fails before and passes after where the app has tests.
3. Same logic in another app (web ↔ linux ↔ ios-suite)? Fix it there too or add a GLOBAL_PLAN task.

## Feature work

1. Tasks with `"needs_go": true` wait for Jonah's go. Don't start them.
2. Put a 3-5 line plan in the PR description first (draft PR is fine), then build.
3. User-facing change → a line in that app's CHANGELOG.md, written for Jonah, not for developers.

## Code review

Follow `.agent/REVIEW.md`. Comments go on the PR; don't push to another agent's branch unless asked. The author
fixes or answers, then re-requests review. Only Jonah merges.

## Style

- Commit message: one plain sentence of what changed for the user. Trailer `Agent: <name/model>` is welcome.
- PR: fill in `.github/pull_request_template.md`. One topic per PR.
- Answers to Jonah: Clear Answer, Confidence Level (0-1, why), Key Caveats. Facts, inferences and guesses kept
  apart; never invent sources or numbers. A little snark is welcome.
- Each app keeps its own code conventions (see its map): ports stay close to the web code, `//!` module docs
  in Rust, `apps/linux/src/maps.rs` is generated (don't hand-edit).
