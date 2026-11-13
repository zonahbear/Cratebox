# Breadcrumbs: Cratebox monorepo (repo-wide)

Short dated index. The full story of each session is its memo in `.handoffs/`; per-app history in `apps/<app>/.claudes/`.

- 2026-11-11 · claude · .handoffs/001_claude_coder.md · Monorepo rebuilt on claude/project-thread-b7gf7r: apps/web,
  apps/linux, apps/ios-suite (current preview/truecurve-usb), root workflows + wrangler.toml, `.agent/` + `.handoffs/`
  handoff layer (Jonah's layout from a Google AI answer, with `apps/` instead of `services/`, his pick: "you pick").
  Jonah's first merge (main 0b52c0a) had conflict markers in 7 files, stale iOS and no truecurve.
- 2026-11-11 · claude · .handoffs/002_claude_coder.md · #16 merged, personal/heat pushed, #31 ported (PR), app/windows releases started, docs cleanup (app maps = AGENTS.md, agents.txt removed). Cloudflare prod build failing: needs log.
- 2026-11-11 · claude · .handoffs/003_claude_coder.md · #18 merged; a4bc095 (Apple half/double-time compare) ported as a PR.
- 2026-11-11 · claude · .handoffs/004_claude_coder.md · PR #19 also ports suite 988438f..99d4b73 (MATCH sort, MIX IN/OUT, Beat grids).
- 2026-11-11 · claude · .handoffs/20261111-2050Z_claude_MONO-12_coder.md · Codex review acted on (rules, claims, memo names, maps, TestFlight NOT BUILT); stick-write rule and sideloading text removed per Jonah.
- 2026-11-11 · claude · .handoffs/20261111-2140Z_claude_ALL-4_coder.md · Antigravity adapter .agents/rules/cratebox.md; PR #19 merged on Jonah's OK.
- 2026-11-11 · claude · .handoffs/20261111-2150Z_claude_MONO-5_debugger.md · #19 merged; Cloudflare production failed again on 24d8b21 (MONO-5 reopened); TestFlight NOT BUILT warning confirmed.
- 2026-11-11 · claude · .handoffs/20261111-2310Z_claude_MONO-6_coder.md · suite 263608d (Touch mode, analysis waits for idle/cool) ported into PR #20.
- 2026-11-12 · claude · .handoffs/20261112-0830Z_claude_AIDJ-1_coder.md · AI DJ (AIDJ-1, PR #21) + Auto trim + Xcode 27 redraw fixes; CI green at dec0bc3; TestFlight goes out with the Settings-tabs stack.
- 2026-11-13 07:10Z: TestFlight 70.1 (hybrid AI DJ, USB analysis, playlist mirror, crash logs, shared Apple analysis by metadata, no duplicates). See .handoffs/LATEST.md.
- 2026-11-13 07:35Z: TestFlight 73.1 (status bubble, copy-what-fits, Report a problem → GitHub with Keychain key). AIDJ-3 planned.
- 2026-11-13 08:06Z: TestFlight 76.1 (analysis queue dedupe, Apple analysis backup/restore on the stick).
- 2026-11-13 08:30Z · claude · .handoffs/20261113-0830Z_claude_DOCS-1_planner.md · TODO.md + handoff docs on main (DOCS-1); iOS code still on PR #24's branch.
- 2026-11-13 09:25Z · claude · .handoffs/20261113-0925Z_claude_USB-3_coder.md · copies broken after restart (/private path) + runaway tally fixed; Sync copies PIONEER; TestFlight 77.1.
- 2026-11-13 09:30Z · claude · Sync copies the entire stick + artwork for copies (78a612e). TestFlight 77 compiled but upload refused by App Store Connect (bundle id lookup) twice; waiting on Jonah.
