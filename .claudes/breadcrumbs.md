# Breadcrumbs: Cratebox monorepo

Per-folder notes stay in `web/.claudes/`, `linux/.claudes/`, `ios-suite/.claudes/`. This file is for repo-wide work.

## 2026-11-11: monorepo rebuilt (branch claude/project-thread-b7gf7r)

- Jonah's first merge on main (0b52c0a) put web + linux in one `services/api/` folder with conflict markers in 7
  files, took iOS from stale main (a99518c, Oct 21) and left truecurve out. Cloudflare build failed on it.
- Rebuilt on top of it: `web/` = Cratebox 0701f9f, `linux/` = Cratebox-Linux 55bfa3a, `ios-suite/` =
  cratebox-iOS-suite preview/truecurve-usb 38194ff (merged with history, original SHAs kept). Each folder's tree
  is byte-identical to its source (checked with `git rev-parse HEAD:<dir>` vs `<sha>^{tree}`), apart from the
  edits below.
- Edits: workflows moved to root `.github/workflows` with `working-directory`; testflight triggers on main +
  `ios-suite/ios/**`; reports.yml writes `web/reports.txt`; wrangler.toml at root with `web/site/` paths; linux
  tests fall back to `../web/tests/music`; cratebox-update tries this repo then Cratebox-Linux;
  cratebox-app.yml mirrors app-latest to Cratebox-Linux when `LEGACY_RELEASE_TOKEN` is set.
- Next: Jonah's call on truecurve (repo is public); move secrets; first Cloudflare build; port iOS PR #31;
  archive old repos only after the checklist in CLAUDE.md "Open work" is empty. Never delete them (releases, PRs).
- Multi-agent handoff (Jonah, 08:08-08:10Z: "easy hand off between Claude, ChatGPT, Gemini and Grok, for code
  reviews, feature and bug work", "with a latest.md and an agents.txt", then a screenshot of the `.handoffs/LATEST.md`
  savestate format): AGENTS.md is the shared map (CLAUDE.md / GEMINI.md import it, nested AGENTS.md per folder,
  Copilot instructions point to it); agents.txt = the same brief in llms.txt layout; `.handoffs/LATEST.md` =
  overwrite-on-handoff savestate with his four sections + In Flight; docs/agents/HANDOFF.md + REVIEW.md; PR template.
