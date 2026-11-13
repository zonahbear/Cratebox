Task DOCS-1 (follow-up) · branch docs/handoff-todo · base main d249ca3 · head = the commit carrying this memo · PR: the open "DOCS-1: …" PR · tree clean after push

## 📍 Where We Stopped
- **Active Task:** DOCS-1 follow-up. Jonah merged #26 (5f21807) and then **PR #24 (d249ca3, 08:25Z)**, so the iOS code is on
  `main` now. This memo only updates the docs that said otherwise. Everything else in the previous memo,
  [20261113-0830Z_claude_DOCS-1_planner.md](20261113-0830Z_claude_DOCS-1_planner.md), still holds: read it and TODO.md.
- **Current State:** new iOS work branches from `main` as `ios/<feature>`. TestFlight still goes through cratebox-iOS-suite
  (MONO-4). Latest TestFlight 76.1 = suite 0c6f8f0 = monorepo ddc6678.
- **Blockers/Bugs:** unchanged (BUG-1..5, CI-1, CI-2; see TODO.md).

## 🛠️ Environmental Verification
- PASSED (verified): `python3 -m json.tool .agent/GLOBAL_PLAN.json` from the repo root. Docs only, no CI.

## 📦 Changes Introduced in This Session
- TODO.md, AGENTS.md, GEMINI.md, .github/copilot-instructions.md, .agents/rules/cratebox.md, .agent/SYSTEM_PROMPT.md,
  .agent/CONTEXT_MAP.md: iOS is on main; dropped the "until #24 merges" exceptions.
- .agent/GLOBAL_PLAN.json: AIDJ-1, ART-1, SET-1, UI-0, USB-2, P1-2 and DOCS-1 → done (device check stays in TODO.md §1).

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Same as the previous memo's steps 2-5. iOS work now branches from main (`ios/<feature>`).
2. [ ] PR #20: check whether #24 already carries suite 263608d; tell Jonah to merge or close it.
