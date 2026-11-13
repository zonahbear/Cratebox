# Current Workspace State

Memo 2026-11-11 21:50Z · agent: claude (debugger) · task MONO-5 · branch claude/project-thread-b7gf7r · base main 24d8b21 · PR (this one) · tree clean after push

## 📍 Where We Stopped
- **Active Task:** MONO-5. The Cloudflare production build is failing again. The previous memo (20261111-2140Z) was wrong to call it resolved.
- **Current State:** PR #19 merged (24d8b21). The production Workers Build failed on 24d8b21, although #19 changed no site files. Nothing to fix in the repo, as far as can be seen from here.
- **Blockers/Bugs:** Needs the Cloudflare build log (Workers → cratebox → Deployments/Builds), which requires Jonah's sign-in.

## 🛠️ Environmental Verification
- Verified (check runs) on main: db99c7f FAIL, 8992a27 FAIL, 4181a99 PASS, 24d8b21 FAIL.
- PASSED at 24d8b21, repo root: `bash apps/web/site/build.sh`.
- PASSED at 24d8b21, repo root: `npx -y wrangler@4 deploy --dry-run`.
- Verified: TestFlight run 43103643432 on 24d8b21 shows the "NOT BUILT / NOT UPLOADED" warning, so it works.

## 📦 Changes Introduced in This Session
- .agent/GLOBAL_PLAN.json: MONO-5 back to blocked with the evidence; MONO-6 and MONO-12 done.

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Jonah: open the failed build for 24d8b21 in the Cloudflare dashboard and paste the log's error lines. Or check Settings → Build: the build command should be `bash apps/web/site/build.sh` or empty (wrangler.toml has it), root directory `/`.
2. [ ] With the log: fix it, then confirm a green production check on the next main push.
3. [ ] HEAT-2 (needs Jonah's go). Jonah: MONO-4, MONO-9, MONO-2, MONO-11. Agents: ALL-2, ALL-3, ALL-5. ALL-4 = Antigravity smoke check on Jonah's machine.
