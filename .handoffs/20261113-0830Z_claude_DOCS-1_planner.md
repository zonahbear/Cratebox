Task DOCS-1 (handoff docs + TODO.md) · branch docs/handoff-todo · base main 0822745 · head = the commit carrying this memo · PR: see GLOBAL_PLAN DOCS-1 / open PR titled "DOCS-1: …" · tree clean after push

## 📍 Where We Stopped
- **Active Task:** DOCS-1 is done and waiting for Jonah's merge. It puts the current state on `main`, so a fresh clone (Codex,
  Antigravity, Gemini, Copilot, Claude) sees it without knowing about PR #24. **The real work in flight is iOS P1-2 and
  phase 3**; read [TODO.md](../TODO.md) for every open item in order and what waits on Jonah.
- **Current State (iOS, verified from git 2026-11-13 08:20Z):** the current iOS app is on branch
  `claude/ios-ai-dj-album-art-settings`, draft PR #24 (head 7224999, 53 commits ahead of main). Latest TestFlight is **76.1** =
  cratebox-iOS-suite `0c6f8f0` (same branch name) = monorepo `ddc6678`. TestFlight still builds from the suite repo because this
  repo has no signing secrets (MONO-4). The full build-by-build log is the previous memo,
  [20261113-0806Z_claude_P1-2_coder.md](20261113-0806Z_claude_P1-2_coder.md).
- **Blockers/Bugs:** open iOS bugs BUG-1..5 (fader-touch crash in an AI DJ transition, copied tracks not playing, stuck
  outside the library, missing tags, launch log noise). Real-track CI waits on Jonah's private repo + TEST_TRACKS_TOKEN
  (CI-1). Crash fetch waits on Jonah's OK (CI-2). Nothing here was tested on a device by me.

## 🛠️ Environmental Verification
- PASSED (verified, this branch): `python3 -m json.tool .agent/GLOBAL_PLAN.json` from the repo root.
- Docs-only change: no app code touched, no CI run. Last iOS CI/TestFlight evidence is in the 0806Z memo (reported here,
  verified by that session): TestFlight 76.1 "UPLOAD SUCCEEDED" 08:00Z, suite run on runner xcode-27.

## 📦 Changes Introduced in This Session
- TODO.md (new): every open item by phase/area, [go]/[Jonah] markers, where the code lives, the rules that bite.
- .agent/GLOBAL_PLAN.json: PR #24's version brought to main, plus new tasks BUG-1..5, CI-1..3, MEM-1, AIDJ-4..6, IOS-2,
  SUG-1, TOUCH-1, UI-5, REL-1..3, LNX-1, IDEA-1, DOCS-1; ART-1/SET-1 → review; PR #24 linked on its tasks.
- .handoffs/: PR #24's memos (20261111-2150Z … 20261113-0806Z) copied unchanged, this memo, LATEST.md = this memo.
- .agent/SYSTEM_PROMPT.md: "Standing rules from Jonah" (branch names `<area>/<short-feature>`, no HEAT/sideloading, Xcode 27
  arm64 only, one CI + one TestFlight per phase, real tracks only, no cloud, grid priority); iOS branch exception in step 4.
- .agent/CONTEXT_MAP.md: TODO.md in the layout; "iOS right now" (PR #24 branch, suite repo builds TestFlight).
- AGENTS.md, GEMINI.md, CLAUDE.md, LLMS.txt, .github/copilot-instructions.md, .agents/rules/cratebox.md: point at TODO.md and
  the iOS branch; Antigravity no longer told to use an `antigravity/` branch prefix.
- .claudes/breadcrumbs.md: PR #24's lines + one for this session.

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Jonah: merge this PR, then PR #24 (on #24's merge, LATEST.md and GLOBAL_PLAN.json may conflict: keep the newer memo
       and this branch's GLOBAL_PLAN, then re-apply any task changes #24 made after 08:20Z).
2. [ ] Jonah: install TestFlight 76.1 and report on it (TODO.md §1); answer the waiting questions there (CI-1 repo + token,
       CI-2 OK, hand-fixed grids, MEM-1, TOUCH-1).
3. [ ] Agent (iOS, on branch `claude/ios-ai-dj-album-art-settings` until #24 merges): BUG-1..5 as Jonah gives details; then
       phase 3 starting with SYNC-3 (measure drift on a real-track test first).
4. [ ] Agent: AIDJ-3 only after Jonah's go, research write-up first.
5. [ ] ALL-4 (Jonah, on his PC): open the repo in Codex and in Antigravity, ask "what are the hard rules, the active task and
       where is the iOS code?" from the root and from apps/ios-suite. Expected: TODO.md, PR #24 branch, the standing rules.
