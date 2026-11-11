# Current Workspace State

Memo 002 · 2026-11-11 08:40Z · agent: claude (coder) · branch: claude/project-thread-b7gf7r

## 📍 Where We Stopped
- **Active Task:** Jonah: "merge 16 and heat, port and publish", then "clean everything up and make it less confusing".
- **Current State:** #16 merged (db99c7f). `personal/heat` pushed (0b5b95c, main merged in). Cleanup PR open (this
  memo). iOS #31 port ready as a separate PR (MONO-6), left unmerged for review. app-latest + windows-latest
  workflows started on main.
- **Blockers/Bugs:** Cloudflare production build FAILED on main (MONO-5); live site unaffected (last good deploy
  stays). Local `npx wrangler@4 deploy --dry-run` passes, so it's likely a dashboard build setting. Needs the log.

## 🛠️ Environmental Verification
- `npx wrangler@4 deploy --dry-run` from the repo root → PASSED (13 asset files, KV + vars bound).
- Same command on the old layout (0701f9f) → PASSED too, so the difference is on Cloudflare's side.
- Port of #31: apps/ios-suite tree == suite branch 28ec954 except AGENTS.md/CLAUDE.md and the moved workflows.
- Not run: iOS tests (macOS only; the other thread runs ios.yml on xcode-27 in the suite repo).

## 📦 Changes Introduced in This Session
- Cleanup: each app's map is now `apps/<app>/AGENTS.md`; `apps/<app>/CLAUDE.md` only imports it.
- Removed `agents.txt` (duplicate of LLMS.txt). Docs point to the app AGENTS.md files.
- `.agent/GLOBAL_PLAN.json`: MONO-1 done, MONO-5 blocked, MONO-6 review, MONO-7 in progress, MONO-9 added.

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Jonah: open the failed Workers Build log (link on the main commit's "Workers Builds: cratebox" check) and
       share the error; or clear any build command / root directory / config path in Workers → cratebox → Settings → Build.
2. [ ] Check releases app-latest and windows-latest in zonahbear/Cratebox (Actions runs of cratebox-app.yml / cratebox-windows.yml).
3. [ ] Review/merge the iOS #31 port PR after the suite thread's xcode-27 screenshots confirm 28ec954 (re-sync if it moved).
4. [ ] Jonah: MONO-9 (delete merged branches, close PR #3), MONO-4 (secrets), MONO-2 (truecurve).
