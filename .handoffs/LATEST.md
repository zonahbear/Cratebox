# Current Workspace State

Memo 2026-11-11 20:50Z · agent: claude (coder) · tasks MONO-12, MONO-6 · branch claude/project-thread-b7gf7r · base main 4181a99 · PR https://github.com/zonahbear/Cratebox/pull/19 · tree clean after push

## 📍 Where We Stopped
- **Active Task:** MONO-12, acting on Codex's read-only handoff review (CODEX_VERIFY.md, main at 4181a99), in the same PR as MONO-6's iOS ports.
- **Current State:** done and waiting on Jonah's OK to merge #19:
  - Jonah's calls: the "no rekordbox stick writes" hard rule is removed (protections kept as a note); every SideStore/sideloading mention is gone.
  - New rules: read-only sessions write nothing; open PRs titled `<TASK-ID>: …` are the claim board; memos are named by UTC time + task.
  - App maps no longer point at the old repos; TestFlight says NOT BUILT / NOT UPLOADED when secrets are missing.
- **Blockers/Bugs:** none new. MONO-5 is resolved: production Cloudflare builds pass on main since 4181a99. PR preview builds still fail, which is known and can be ignored. TestFlight secrets are still missing (MONO-4).

## 🛠️ Environmental Verification
- Verified (GitHub check runs): production Workers Build failed on db99c7f, 8992a27 and d9acf81, then passed on 4181a99 (08:28Z).
- Verified: TestFlight run 42987007476 on 4181a99 was "success" with every build step skipped (secrets missing).
- PASSED: `python3 -c "import yaml;yaml.safe_load(open('.github/workflows/testflight.yml'))"` (repo root).
- PASSED: GLOBAL_PLAN parses, ids are unique, deps exist.
- Not run: the new NOT BUILT summary. It shows on the next testflight.yml run (merging this PR triggers one, which skips).
- Not run: app tests. Docs and workflow text only, no app code.

## 📦 Changes Introduced in This Session
- .agent/SYSTEM_PROMPT.md: stick-write hard rule removed (protections as a note), rule 5 reworded, Scope section, PR claims, new memo name + header line, reported vs verified.
- .agent/REVIEW.md, .github/pull_request_template.md, .github/copilot-instructions.md: match the rule changes.
- .agent/CONTEXT_MAP.md, LLMS.txt: new memo naming; TestFlight green ≠ shipped.
- .agent/GLOBAL_PLAN.json: MONO-5 done, MONO-6 review (#19), MONO-7 split (MONO-11), MONO-12 added, follow-ups ALL-2..5, HEAT-2.
- .github/workflows/testflight.yml: NOT BUILT / NOT UPLOADED warning + job summary when secrets are missing.
- .github/workflows/ios.yml: header comment.
- apps/web/AGENTS.md: Pages, wrangler, workflows, branches, cross-app, CRATEBOX_CHROME without a glob.
- apps/linux/AGENTS.md: test fallback ../web, branches, root workflows, cross-app, stick-write note.
- apps/ios-suite/AGENTS.md, README.md, ios/TESTFLIGHT.md, ios/project.yml: TestFlight-only install text.

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Jonah: OK to merge PR #19.
2. [ ] After merge: HEAT-2 (merge main into personal/heat, never the reverse), needs Jonah's go.
3. [ ] Jonah: MONO-4 (secrets), MONO-9 (merged branches, PR #3), MONO-2 (truecurve), MONO-11 (old updaters).
4. [ ] Agents: ALL-2 (web ↔ ios-suite mirror check), ALL-3 (verify entry points), ALL-5 (metadata check). ALL-4 needs Jonah to name the tool.
