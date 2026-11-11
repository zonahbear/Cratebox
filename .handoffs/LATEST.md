# Current Workspace State

Memo 2026-11-11 21:40Z · agent: claude (coder) · task ALL-4 (+ MONO-6, MONO-12) · branch claude/project-thread-b7gf7r · base main 4181a99 · PR https://github.com/zonahbear/Cratebox/pull/19 · tree clean after push

## 📍 Where We Stopped
- **Active Task:** ALL-4. Jonah confirmed "antimatter" means Google Antigravity. He OK'd merging PR #19 (iOS ports + Codex review docs fixes, see memo 20261111-2050Z).
- **Current State:** Antigravity adapter `.agents/rules/cratebox.md` added. It's a pointer to the shared files only. PR #19 is being merged.
- **Blockers/Bugs:** MONO-4 (TestFlight secrets) is unchanged. The adapter's auto-loading is unverified until someone opens the repo in Antigravity.

## 🛠️ Environmental Verification
- Reported, not verified: the search summary of antigravity.google/docs/rules says Antigravity reads AGENTS.md, GEMINI.md and `.agents/rules/*.md`. The page itself isn't reachable from the cloud session.
- PASSED: GLOBAL_PLAN parses (`python3 -m json.tool .agent/GLOBAL_PLAN.json`, repo root).

## 📦 Changes Introduced in This Session
- .agents/rules/cratebox.md: new Antigravity adapter.
- .agent/CONTEXT_MAP.md: lists the adapter.
- .agent/SYSTEM_PROMPT.md: `antigravity/` branch prefix.
- .agent/GLOBAL_PLAN.json: ALL-4 is now the smoke check only.

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Jonah (on his machine): open the repo in Antigravity and ask it "what are the hard rules and the active task?" from the root and from apps/web.
2. [ ] HEAT-2: merge main into personal/heat (needs Jonah's go).
3. [ ] Jonah: MONO-4, MONO-9, MONO-2, MONO-11.
4. [ ] Agents: ALL-2, ALL-3, ALL-5.
